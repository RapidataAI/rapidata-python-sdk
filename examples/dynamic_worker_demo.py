"""
Demonstration of Dynamic Worker Adjustment Feature

This script shows how the dynamic worker adjustment feature works
and how to configure it for different use cases.
"""

from rapidata import RapidataClient, rapidata_config
from rapidata.rapidata_client.datapoints import Datapoint


def demo_default_behavior():
    """
    Demo 1: Default behavior (dynamic workers enabled)

    The system will:
    1. Check ~/.rapidata/worker_config.json for learned optimal workers
    2. If not found, calculate from CPU cores (2 × cpu_count)
    3. Process in batches of 1000 items
    4. Adjust workers between batches based on performance
    5. Save learned configuration for next time
    """
    print("=" * 60)
    print("Demo 1: Default Behavior (Dynamic Workers Enabled)")
    print("=" * 60)

    client = RapidataClient()
    dataset = client.dataset.get_or_create("demo-dynamic-workers")

    # Create sample datapoints
    datapoints = [
        Datapoint(
            asset=f"https://example.com/image_{i}.jpg",
            data_type="media"
        )
        for i in range(2500)  # 2500 items = ~3 batches at 1000/batch
    ]

    print(f"\nUploading {len(datapoints)} datapoints...")
    print("Watch the logs for worker adjustments between batches!")
    print()

    # Upload - dynamic adjustment happens automatically
    successful, failed = dataset.add_datapoints(datapoints)

    print(f"\nUpload complete: {len(successful)} successful, {len(failed)} failed")
    print(f"Learned worker count saved to ~/.rapidata/worker_config.json")
    print()


def demo_static_mode():
    """
    Demo 2: Static mode (original behavior)

    Disable dynamic workers to use the original fixed worker count.
    This is useful for debugging or when you want predictable behavior.
    """
    print("=" * 60)
    print("Demo 2: Static Mode (Original Behavior)")
    print("=" * 60)

    # Disable dynamic workers
    rapidata_config.upload.enableDynamicWorkers = False
    rapidata_config.upload.maxWorkers = 25

    print(f"Dynamic workers: {rapidata_config.upload.enableDynamicWorkers}")
    print(f"Fixed worker count: {rapidata_config.upload.maxWorkers}")
    print()

    client = RapidataClient()
    dataset = client.dataset.get_or_create("demo-static-workers")

    # Create sample datapoints
    datapoints = [
        Datapoint(
            asset=f"https://example.com/image_{i}.jpg",
            data_type="media"
        )
        for i in range(100)
    ]

    print(f"Uploading {len(datapoints)} datapoints...")
    print("No batching or worker adjustments will occur.")
    print()

    # Upload - uses fixed 25 workers throughout
    successful, failed = dataset.add_datapoints(datapoints)

    print(f"\nUpload complete: {len(successful)} successful, {len(failed)} failed")
    print()

    # Re-enable dynamic workers for other demos
    rapidata_config.upload.enableDynamicWorkers = True


def demo_custom_configuration():
    """
    Demo 3: Custom configuration

    Fine-tune the dynamic worker behavior for your specific needs.
    """
    print("=" * 60)
    print("Demo 3: Custom Configuration")
    print("=" * 60)

    # Conservative settings (prioritize reliability)
    rapidata_config.upload.enableDynamicWorkers = True
    rapidata_config.upload.batchSize = 500  # Smaller batches
    rapidata_config.upload.minWorkers = 10  # Higher minimum
    rapidata_config.upload.maxWorkersLimit = 50  # Lower maximum

    print("Custom configuration:")
    print(f"  - Batch size: {rapidata_config.upload.batchSize}")
    print(f"  - Min workers: {rapidata_config.upload.minWorkers}")
    print(f"  - Max workers limit: {rapidata_config.upload.maxWorkersLimit}")
    print()

    client = RapidataClient()
    dataset = client.dataset.get_or_create("demo-custom-config")

    # Create sample datapoints
    datapoints = [
        Datapoint(
            asset=f"https://example.com/image_{i}.jpg",
            data_type="media"
        )
        for i in range(1000)
    ]

    print(f"Uploading {len(datapoints)} datapoints...")
    print("Using conservative settings for maximum reliability.")
    print()

    # Upload with custom settings
    successful, failed = dataset.add_datapoints(datapoints)

    print(f"\nUpload complete: {len(successful)} successful, {len(failed)} failed")
    print()

    # Reset to defaults
    rapidata_config.upload.batchSize = 1000
    rapidata_config.upload.minWorkers = 5
    rapidata_config.upload.maxWorkersLimit = 200


def demo_monitoring():
    """
    Demo 4: Monitoring worker adjustments

    Shows how to observe the dynamic adjustment process.
    """
    print("=" * 60)
    print("Demo 4: Monitoring Worker Adjustments")
    print("=" * 60)

    # Enable detailed logging
    import logging
    logging.basicConfig(level=logging.INFO)

    print("Enabled INFO logging to see detailed worker adjustments.")
    print("Look for log messages like:")
    print("  - 'Processing batch of X items with Y workers'")
    print("  - 'Batch complete: X items/sec, Y% error rate'")
    print("  - 'Worker adjustment: X → Y. Reason: ...'")
    print()

    client = RapidataClient()
    dataset = client.dataset.get_or_create("demo-monitoring")

    # Create sample datapoints
    datapoints = [
        Datapoint(
            asset=f"https://example.com/image_{i}.jpg",
            data_type="media"
        )
        for i in range(3000)  # ~3 batches
    ]

    print(f"Uploading {len(datapoints)} datapoints...")
    print()

    # Upload - watch the logs!
    successful, failed = dataset.add_datapoints(datapoints)

    print(f"\nUpload complete: {len(successful)} successful, {len(failed)} failed")
    print()


def demo_persistence():
    """
    Demo 5: Configuration persistence

    Shows how learned configuration persists across sessions.
    """
    print("=" * 60)
    print("Demo 5: Configuration Persistence")
    print("=" * 60)

    from pathlib import Path
    import json

    config_path = Path.home() / ".rapidata" / "worker_config.json"

    print(f"Configuration file: {config_path}")

    if config_path.exists():
        print("\nCurrent saved configuration:")
        with open(config_path, "r") as f:
            config_data = json.load(f)
        print(json.dumps(config_data, indent=2))
    else:
        print("\nNo saved configuration found (will be created after first upload).")

    print("\nPerforming upload to update learned configuration...")

    client = RapidataClient()
    dataset = client.dataset.get_or_create("demo-persistence")

    # Create sample datapoints
    datapoints = [
        Datapoint(
            asset=f"https://example.com/image_{i}.jpg",
            data_type="media"
        )
        for i in range(500)
    ]

    successful, failed = dataset.add_datapoints(datapoints)

    print(f"\nUpload complete: {len(successful)} successful, {len(failed)} failed")

    if config_path.exists():
        print("\nUpdated saved configuration:")
        with open(config_path, "r") as f:
            config_data = json.load(f)
        print(json.dumps(config_data, indent=2))

    print("\nThis configuration will be used as the starting point for future uploads.")
    print()


if __name__ == "__main__":
    print()
    print("=" * 60)
    print("Dynamic Worker Adjustment Demonstration")
    print("=" * 60)
    print()
    print("This demo shows the new dynamic worker adjustment feature.")
    print("Choose a demo to run:")
    print()
    print("1. Default behavior (recommended)")
    print("2. Static mode (backward compatible)")
    print("3. Custom configuration")
    print("4. Monitoring worker adjustments")
    print("5. Configuration persistence")
    print()

    choice = input("Enter demo number (1-5) or 'all': ").strip()

    if choice == "1":
        demo_default_behavior()
    elif choice == "2":
        demo_static_mode()
    elif choice == "3":
        demo_custom_configuration()
    elif choice == "4":
        demo_monitoring()
    elif choice == "5":
        demo_persistence()
    elif choice.lower() == "all":
        demo_default_behavior()
        demo_static_mode()
        demo_custom_configuration()
        demo_monitoring()
        demo_persistence()
    else:
        print("Invalid choice. Please run again and select 1-5 or 'all'.")

    print()
    print("=" * 60)
    print("Demo Complete")
    print("=" * 60)
    print()
