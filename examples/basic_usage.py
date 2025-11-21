from maico import MaicoController, MaicoConfig, TriggerSource, OutputTriggerKind


def main_real_hardware():
    print("=== Real Hardware Mode ===")
    config = MaicoConfig(
        device_index=0,
        trigger_source=TriggerSource.SOFTWARE,
        output_trigger_kind=OutputTriggerKind.EXPOSURE,
        exposure_time_ms=10.0,
        max_power_percent=80,
        simulation_mode=False
    )
    
    run_demo(config)


def main_simulation():
    print("=== Simulation Mode ===")
    config = MaicoConfig(
        device_index=0,
        trigger_source=TriggerSource.SOFTWARE,
        output_trigger_kind=OutputTriggerKind.EXPOSURE,
        exposure_time_ms=10.0,
        max_power_percent=80,
        simulation_mode=True
    )
    
    run_demo(config)


def run_demo(config: MaicoConfig):
    controller = MaicoController(config)
    
    init_result = controller.initialize()
    if init_result.is_err():
        print(f"Initialization failed: {init_result.unwrap_err()}")
        return
    
    print("✓ Controller initialized successfully")
    
    power_result = controller.set_power(50)
    if power_result.is_err():
        print(f"Failed to set power: {power_result.unwrap_err()}")
        return
    
    print("✓ Power set to 50%")
    
    status = controller.get_status()
    print(f"Current state: {status.state.name}")
    print(f"Temperature: {status.temperature_celsius}°C")
    print(f"Simulation mode: {status.simulation_mode}")
    
    laser_on_result = controller.laser_on()
    if laser_on_result.is_err():
        print(f"Failed to activate laser: {laser_on_result.unwrap_err()}")
        return
    
    print("✓ Laser activated")
    
    import time
    time.sleep(2)
    
    laser_off_result = controller.laser_off()
    if laser_off_result.is_err():
        print(f"Failed to deactivate laser: {laser_off_result.unwrap_err()}")
        return
    
    print("✓ Laser deactivated")
    
    shutdown_result = controller.shutdown()
    if shutdown_result.is_err():
        print(f"Shutdown failed: {shutdown_result.unwrap_err()}")
        return
    
    print("✓ Controller shutdown successfully")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--real":
        main_real_hardware()
    else:
        main_simulation()
