import argparse
import logging
import sys
from pathlib import Path
from .config import Settings
from .storage import Storage, default_data_dir


def main():
    p = argparse.ArgumentParser(description="Experimental local mouth-movement recorder")
    p.add_argument("--data-dir", type=Path, help="Override local application data folder")
    p.add_argument("--config", type=Path, help="JSON settings file")
    p.add_argument("--download-model", action="store_true")
    p.add_argument("--simulate", action="store_true", help="Complete a deterministic synthetic assessment without the UI")
    p.add_argument("--analyze-video", type=Path, help="Analyze timestamped video without the UI")
    p.add_argument("--synthetic-video", action="store_true", help="Explicitly label analyzed video as synthetic")
    p.add_argument("--export", type=Path, help="CSV destination for batch mode")
    args = p.parse_args()
    root = args.data_dir or default_data_dir()
    root.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(root / "application.log")])
    cfg = Settings.read(args.config) if args.config else Settings()
    if args.download_model:
        from .model import ensure_model
        print("Face model ready:", ensure_model())
        return 0
    if args.simulate or args.analyze_video:
        from .replay import run_synthetic, analyze_video
        store = Storage(root)
        try:
            sid = run_synthetic(store, cfg) if args.simulate else analyze_video(args.analyze_video, store, cfg, synthetic=args.synthetic_video)
            meta, rows = store.load(sid)
            if args.export:
                print("Exported:", store.export(sid, args.export))
            print(f"Saved and reopened {sid}: {meta['status']}, {len(rows)} frames, simulated={meta['simulated']}")
        finally:
            store.close()
        return 0
    from PySide6.QtWidgets import QApplication
    from .ui import MainWindow
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Jaw Recovery Monitor")
    window = MainWindow(root, cfg)
    window.show()
    logging.info("Application started; UI shown")
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
