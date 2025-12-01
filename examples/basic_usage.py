#!/usr/bin/env python3
"""pylib-maico Basic Usage Example

Demonstrates the complete laser control sequence for MAICO C15890.

Key Discovery from SI Code Analysis:
    The MAICO hardware requires cap_start() to physically enable laser output.
    Simply setting SUBUNIT_CONTROL to ON is not sufficient.
    
    Correct sequence:
    1. Set SUBUNIT_CONTROL to ON
    2. Set SUBUNIT_LASERPOWER to desired value
    3. Allocate buffer (buf_alloc)
    4. Start capture (cap_start) ← This enables physical laser output!
"""

from maico import (
    MaicoController,
    MaicoConfig,
    TriggerSource,
    OutputTriggerKind,
    SubunitConfig,
)


def main() -> None:
    config = MaicoConfig(
        device_index=0,
        trigger_source=TriggerSource.SOFTWARE,
        output_trigger_kind=OutputTriggerKind.EXPOSURE,
        exposure_time_ms=10.0,
        max_power_percent=100,
        simulation_mode=True,
        buffer_frame_count=3,
        subunits=(
            SubunitConfig(index=0, power_percent=30),
        ),
    )
    
    controller = MaicoController(config)
    
    print("=== MAICO Controller Example ===\n")
    
    print("[1] Initializing controller...")
    init_result = controller.initialize()
    if init_result.is_err():
        print(f"    [FAIL] {init_result.unwrap_err()}")
        return
    print("    [OK] Controller initialized")
    
    status = controller.get_status()
    print(f"\n[2] Initial Status:")
    print(f"    State: {status.state.name}")
    print(f"    Laser ON: {status.is_laser_on}")
    print(f"    Capture Running: {status.is_capture_running}")
    print(f"    Temperature: {status.temperature_celsius}C")
    print(f"    Simulation Mode: {status.simulation_mode}")
    
    if status.active_subunits:
        print(f"    Subunits ({len(status.active_subunits)}):")
        for su in status.active_subunits:
            state = "ON" if su.is_on else "OFF"
            installed = "Installed" if su.is_installed else "Not Installed"
            print(f"      [{su.index}] {su.wavelength_nm}nm - {state} - Power: {su.power_percent}% - {installed}")
    
    print("\n[3] Turning laser ON (subunit 0, power 50%)...")
    on_result = controller.laser_on(subunit_index=0, power_percent=50)
    if on_result.is_err():
        print(f"    [FAIL] {on_result.unwrap_err()}")
    else:
        print("    [OK] Laser is now ON")
        print("    [INFO] cap_start() was called - physical laser output enabled!")
    
    status = controller.get_status()
    print(f"\n[4] Status After Laser ON:")
    print(f"    State: {status.state.name}")
    print(f"    Laser ON: {status.is_laser_on}")
    print(f"    Capture Running: {status.is_capture_running}")
    
    print("\n[5] Adjusting power to 75%...")
    power_result = controller.set_power(75)
    if power_result.is_err():
        print(f"    [FAIL] {power_result.unwrap_err()}")
    else:
        print("    [OK] Power adjusted to 75%")
    
    print("\n[6] Turning laser OFF...")
    off_result = controller.laser_off()
    if off_result.is_err():
        print(f"    [FAIL] {off_result.unwrap_err()}")
    else:
        print("    [OK] Laser is now OFF")
        print("    [INFO] cap_stop() was called - physical laser output disabled!")
    
    status = controller.get_status()
    print(f"\n[7] Status After Laser OFF:")
    print(f"    State: {status.state.name}")
    print(f"    Laser ON: {status.is_laser_on}")
    print(f"    Capture Running: {status.is_capture_running}")
    
    print("\n[8] Shutting down...")
    shutdown_result = controller.shutdown()
    if shutdown_result.is_err():
        print(f"    [FAIL] {shutdown_result.unwrap_err()}")
    else:
        print("    [OK] Controller shut down")
    
    print("\n=== Example Complete ===")


if __name__ == "__main__":
    main()
