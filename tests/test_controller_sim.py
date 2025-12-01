#!/usr/bin/env python3
"""Controller Simulation Mode Tests

Tests the complete laser control sequence including:
- Buffer allocation
- Subunit control
- Capture start/stop (which enables/disables physical laser output)
"""

import pytest
from maico import (
    MaicoController,
    MaicoConfig,
    MaicoState,
    TriggerSource,
    OutputTriggerKind,
    SubunitConfig,
)


@pytest.fixture
def sim_config() -> MaicoConfig:
    return MaicoConfig(
        device_index=0,
        trigger_source=TriggerSource.SOFTWARE,
        output_trigger_kind=OutputTriggerKind.EXPOSURE,
        exposure_time_ms=10.0,
        max_power_percent=100,
        simulation_mode=True,
        buffer_frame_count=3,
    )


@pytest.fixture
def controller(sim_config: MaicoConfig) -> MaicoController:
    return MaicoController(sim_config)


class TestControllerInitialization:
    def test_initialize_success(self, controller: MaicoController) -> None:
        result = controller.initialize()
        
        assert result.is_ok()
        status = controller.get_status()
        assert status.state == MaicoState.LASER_OFF
        assert not status.is_laser_on
        assert not status.is_capture_running

    def test_double_initialize_fails(self, controller: MaicoController) -> None:
        controller.initialize()
        result = controller.initialize()
        
        assert result.is_err()


class TestLaserControl:
    def test_laser_on_starts_capture(self, controller: MaicoController) -> None:
        controller.initialize()
        
        result = controller.laser_on(subunit_index=0, power_percent=50)
        
        assert result.is_ok()
        status = controller.get_status()
        assert status.is_laser_on
        assert status.is_capture_running
        assert status.state == MaicoState.LASER_ON

    def test_laser_off_stops_capture(self, controller: MaicoController) -> None:
        controller.initialize()
        controller.laser_on(subunit_index=0, power_percent=50)
        
        result = controller.laser_off()
        
        assert result.is_ok()
        status = controller.get_status()
        assert not status.is_laser_on
        assert not status.is_capture_running
        assert status.state == MaicoState.LASER_OFF

    def test_laser_on_without_initialize_fails(self, controller: MaicoController) -> None:
        result = controller.laser_on(subunit_index=0, power_percent=50)
        
        assert result.is_err()

    def test_laser_off_without_laser_on_fails(self, controller: MaicoController) -> None:
        controller.initialize()
        
        result = controller.laser_off()
        
        assert result.is_err()


class TestPowerControl:
    def test_set_power_while_laser_on(self, controller: MaicoController) -> None:
        controller.initialize()
        controller.laser_on(subunit_index=0, power_percent=30)
        
        result = controller.set_power(75)
        
        assert result.is_ok()

    def test_set_power_over_limit_fails(self, controller: MaicoController) -> None:
        controller.initialize()
        controller.laser_on(subunit_index=0, power_percent=30)
        
        result = controller.set_power(150)
        
        assert result.is_err()


class TestSubunitStatus:
    def test_get_subunit_status(self, controller: MaicoController) -> None:
        controller.initialize()
        
        status = controller.get_status()
        
        assert len(status.active_subunits) > 0
        for subunit in status.active_subunits:
            assert subunit.is_installed
            assert subunit.wavelength_nm > 0


class TestShutdown:
    def test_shutdown_from_laser_off(self, controller: MaicoController) -> None:
        controller.initialize()
        
        result = controller.shutdown()
        
        assert result.is_ok()
        status = controller.get_status()
        assert status.state == MaicoState.SHUTDOWN

    def test_shutdown_with_laser_on_turns_off_first(self, controller: MaicoController) -> None:
        controller.initialize()
        controller.laser_on(subunit_index=0, power_percent=50)
        
        result = controller.shutdown()
        
        assert result.is_ok()
        status = controller.get_status()
        assert status.state == MaicoState.SHUTDOWN
        assert not status.is_laser_on
        assert not status.is_capture_running


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
