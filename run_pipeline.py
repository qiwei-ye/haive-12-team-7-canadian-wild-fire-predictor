"""Pipeline entry point; display configuration until data stages are implemented."""

from scr import config


def main() -> None:
    """Report the inclusive time windows used by the project."""
    print("Configured time windows (inclusive):")
    for name, (start_date, end_date) in config.TIME_WINDOWS.items():
        print(f"{name}: {start_date} to {end_date}")


if __name__ == "__main__":
    main()
