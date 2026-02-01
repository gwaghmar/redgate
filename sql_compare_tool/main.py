from gui.main_window import launch
from utils.logger import setup_logger


if __name__ == "__main__":
    # Initialize logging system
    setup_logger("sql_compare_tool")
    launch()
