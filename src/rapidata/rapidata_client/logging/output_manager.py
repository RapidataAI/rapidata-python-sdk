class RapidataOutputManager:
    """Manages print outputs and progress bars for the Rapidata module."""
    
    silent_mode: bool = False

    @classmethod
    def enable_silent_mode(cls) -> None:
        """Enable silent mode, suppressing all print outputs and progress bars, not logging."""
        cls.silent_mode = True

    @classmethod
    def disable_silent_mode(cls) -> None:
        """Disable silent mode, allowing outputs to be printed.
        This is the default behavior.
        """
        cls.silent_mode = False

def managed_print(*args, **kwargs) -> None:
    if not RapidataOutputManager.silent_mode:
        print(*args, **kwargs)
