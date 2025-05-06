class OutputManger:
    silent_mode = False
    
    @classmethod
    def enable_silent_mode(cls):
        cls.silent_mode = True
        
    @classmethod
    def disable_silent_mode(cls):
        cls.silent_mode = False

def managed_print(*args, **kwargs):
    if not OutputManger.silent_mode:
        print(*args, **kwargs)


