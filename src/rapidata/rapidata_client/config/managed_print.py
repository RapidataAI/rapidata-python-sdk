from rapidata.rapidata_client.config import rapidata_config


def managed_print(*args, **kwargs) -> None:
    if not rapidata_config.logging.silent_mode:
        print(*args, **kwargs)
