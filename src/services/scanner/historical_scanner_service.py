"""Historical Scanner Service orchestrating multi-device scanning and storage workflow.

Workflow:
1. Concurrently connects to selected Cisco switches via CiscoDataCollector.
2. Collects current snapshots and combines with historical data from Excel.
3. Computes multi-scan historical metrics via HistoricalAnalyzer.
4. Evaluates safety classification via RiskProtectionEngine.
5. Persists results to data/port_history.xlsx (with auto-backup and atomic write).
6. Notifies GUI of progress and completion.
"""

import concurrent.futures
import threading
import time
import uuid
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set, Tuple

from core.inventory import SwitchDevice
from core.logger import logger
from core.scanner_models import (
    PortClassification,
    PortSnapshot,
    PortSummaryRecord,
    ProtectedPortRecord,
    ScanLogRecord,
    ScanSettings,
    SwitchScanResult,
)
from services.scanner.cisco_collector import CiscoDataCollector
from services.scanner.excel_storage import ExcelStorageManager
from services.scanner.historical_analyzer import HistoricalAnalyzer
from services.scanner.risk_protection_engine import RiskProtectionEngine


class HistoricalScannerService:
    """Coordinates the historical port scanning and Excel persistence pipeline."""

    def __init__(
        self,
        storage_manager: Optional[ExcelStorageManager] = None,
        settings: Optional[ScanSettings] = None,
        max_workers: int = 5,
    ):
        self.storage = storage_manager or ExcelStorageManager()
        self.settings = settings or ScanSettings()
        self.max_workers = max_workers
        self.analyzer = HistoricalAnalyzer(self.settings)
        self.protection_engine = RiskProtectionEngine(self.settings)
        self._is_cancelled = False

    def cancel_scan(self) -> None:
        """Signals current batch scan to stop."""
        self._is_cancelled = True
        logger.warning("Đã gửi tín hiệu hủy phiên quét.")

    def run_batch_scan(
        self,
        devices: List[SwitchDevice],
        on_switch_started: Optional[Callable[[SwitchDevice], None]] = None,
        on_switch_complete: Optional[Callable[[SwitchDevice, SwitchScanResult], None]] = None,
        on_all_complete: Optional[Callable[[List[PortSummaryRecord], ScanLogRecord], None]] = None,
        on_log_message: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Executes full scan pipeline across multiple devices in background threads."""
        self._is_cancelled = False
        start_time = time.time()
        scan_id = f"SCAN_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:4]}"
        scan_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        def _log(msg: str):
            logger.info(msg)
            if on_log_message:
                try:
                    on_log_message(msg)
                except Exception:
                    pass

        def _worker(device: SwitchDevice) -> SwitchScanResult:
            if self._is_cancelled:
                return SwitchScanResult(
                    switch_name=device.name,
                    switch_ip=device.ip,
                    success=False,
                    error_message="Phiên quét đã bị hủy bởi người dùng.",
                )
            if on_switch_started:
                try:
                    on_switch_started(device)
                except Exception:
                    pass

            collector = CiscoDataCollector(device, self.settings)
            result = collector.collect(log_callback=on_log_message)

            if on_switch_complete:
                try:
                    on_switch_complete(device, result)
                except Exception:
                    pass

            return result

        def _run():
            _log(f"=== BẮT ĐẦU PHIÊN QUÉT {scan_id} TRÊN {len(devices)} SWITCH ===")
            all_new_snapshots: List[PortSnapshot] = []
            switch_results: List[SwitchScanResult] = []
            success_count = 0
            fail_count = 0

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_device = {executor.submit(_worker, dev): dev for dev in devices}
                for future in concurrent.futures.as_completed(future_to_device):
                    dev = future_to_device[future]
                    try:
                        res = future.result()
                        switch_results.append(res)
                        if res.success:
                            success_count += 1
                            all_new_snapshots.extend(res.snapshots)
                            _log(f"Hoàn thành quét switch {dev.name}: {len(res.snapshots)} ports.")
                        else:
                            fail_count += 1
                            _log(f"Lỗi khi quét switch {dev.name}: {res.error_message}")
                    except Exception as e:
                        fail_count += 1
                        err_msg = f"Ngoại lệ khi quét {dev.name}: {e}"
                        _log(err_msg)
                        switch_results.append(SwitchScanResult(
                            switch_name=dev.name,
                            switch_ip=dev.ip,
                            success=False,
                            error_message=str(e),
                        ))

            if self._is_cancelled:
                _log("Phiên quét đã dừng lại theo yêu cầu.")

            _log("Đang tải dữ liệu lịch sử từ tệp Excel port_history.xlsx...")
            # Load existing historical data and protected ports
            try:
                prev_summaries = self.storage.load_port_summaries()
                protected_records = self.storage.load_protected_ports()
            except Exception as e:
                _log(f"Cảnh báo khi đọc dữ liệu cũ: {e}. Sẽ phân tích dữ liệu mới.")
                prev_summaries = []
                protected_records = []

            protected_set = {(p.switch_name, p.interface) for p in protected_records}

            # Run Historical Analysis
            _log("Đang phân tích chỉ số lịch sử và các chuỗi scan...")
            updated_summaries = self.analyzer.analyze(
                current_snapshots=all_new_snapshots,
                previous_summaries=prev_summaries,
                protected_ports_set=protected_set,
            )

            # Run Risk & Protection Engine
            _log("Đang áp dụng bộ quy tắc đánh giá rủi ro và phân loại an toàn...")
            updated_summaries = self.protection_engine.evaluate_all(
                summaries=updated_summaries,
                protected_ports_set=protected_set,
            )

            # Compute scan log metrics
            duration_total = time.time() - start_time
            total_ports = len(updated_summaries)
            active_cnt = sum(1 for p in updated_summaries if p.classification == PortClassification.ACTIVE)
            unused_cnt = sum(1 for p in updated_summaries if p.classification == PortClassification.UNUSED)
            monitor_cnt = sum(1 for p in updated_summaries if p.classification == PortClassification.MONITOR)
            prot_cnt = sum(1 for p in updated_summaries if p.classification == PortClassification.PROTECTED)
            trunk_cnt = sum(1 for p in updated_summaries if p.classification in (PortClassification.TRUNK_UPLINK, PortClassification.PORT_CHANNEL))
            err_cnt = sum(1 for p in updated_summaries if p.classification == PortClassification.ERROR)

            status_str = "SUCCESS" if fail_count == 0 else ("PARTIAL" if success_count > 0 else "FAILED")
            notes_str = f"Quét {len(devices)} switches ({success_count} thành công, {fail_count} thất bại)"

            scan_log = ScanLogRecord(
                scan_id=scan_id,
                timestamp=scan_time_str,
                switches_scanned=len(devices),
                total_ports=total_ports,
                active_count=active_cnt,
                unused_count=unused_cnt,
                monitor_count=monitor_cnt,
                protected_count=prot_cnt,
                trunk_count=trunk_cnt,
                error_count=err_cnt,
                duration_seconds=duration_total,
                status=status_str,
                notes=notes_str,
            )

            # Save results into Excel storage (auto-backup + atomic write)
            _log("Đang lưu kết quả vào tệp Excel persistent storage...")
            try:
                self.storage.save_scan_results(
                    new_snapshots=all_new_snapshots,
                    updated_summaries=updated_summaries,
                    scan_log=scan_log,
                )
                _log("Đã cập nhật đầy đủ 4 trang tính trong port_history.xlsx thành công!")
            except Exception as e:
                _log(f"LỖI LƯU DỮ LIỆU EXCEL: {e}")

            _log(f"=== KẾT THÚC PHIÊN QUÉT ({duration_total:.2f}s): {unused_cnt} port UNUSED, {active_cnt} port ACTIVE ===")

            if on_all_complete:
                try:
                    on_all_complete(updated_summaries, scan_log)
                except Exception as e:
                    logger.error(f"Lỗi trong callback on_all_complete: {e}")

        threading.Thread(target=_run, daemon=True).start()
