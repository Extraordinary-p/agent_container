def format_size(size_bytes: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

def print_separator(char: str = "=", length: int = 80) -> None:
    print(char * length)

class colored_output:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
    @classmethod
    def success(cls, text: str) -> str:
        return f"{cls.OKGREEN}{text}{cls.ENDC}"
    
    @classmethod
    def warning(cls, text: str) -> str:
        return f"{cls.WARNING}{text}{cls.ENDC}"
    
    @classmethod
    def error(cls, text: str) -> str:
        return f"{cls.FAIL}{text}{cls.ENDC}"
    
    @classmethod
    def info(cls, text: str) -> str:
        return f"{cls.OKBLUE}{text}{cls.ENDC}"
