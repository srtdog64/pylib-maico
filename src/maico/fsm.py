from typing import Callable
from .types import MaicoState, Result
from .errors import MaicoError, ErrorCode, create_error


StateTransitionGuard = Callable[[MaicoState, MaicoState], Result[bool, MaicoError]]


class MaicoFSM:
    def __init__(self, initial_state: MaicoState = MaicoState.UNINITIALIZED) -> None:
        self._current_state = initial_state
        self._transition_table: dict[tuple[MaicoState, MaicoState], bool] = {}
        self._guards: list[StateTransitionGuard] = []
        self._initialize_transitions()

    def _initialize_transitions(self) -> None:
        valid_transitions = [
            (MaicoState.UNINITIALIZED, MaicoState.INITIALIZED),
            (MaicoState.INITIALIZED, MaicoState.READY),
            (MaicoState.READY, MaicoState.LASER_OFF),
            (MaicoState.LASER_OFF, MaicoState.LASER_ON),
            (MaicoState.LASER_ON, MaicoState.LASER_OFF),
            (MaicoState.LASER_OFF, MaicoState.READY),
            (MaicoState.READY, MaicoState.SHUTDOWN),
        ]

        for from_state, to_state in valid_transitions:
            self._transition_table[(from_state, to_state)] = True

        for state in MaicoState:
            self._transition_table[(state, MaicoState.ERROR)] = True

    def add_guard(self, guard: StateTransitionGuard) -> None:
        self._guards.append(guard)

    def get_current_state(self) -> MaicoState:
        return self._current_state

    def can_transition(self, to_state: MaicoState) -> bool:
        return self._transition_table.get((self._current_state, to_state), False)

    def transition(self, to_state: MaicoState) -> Result[MaicoState, MaicoError]:
        if not self.can_transition(to_state):
            return Result.err(create_error(
                ErrorCode.INVALID_STATE_TRANSITION,
                f"Cannot transition from {self._current_state.name} to {to_state.name}",
                from_state=self._current_state.name,
                to_state=to_state.name
            ))

        for guard in self._guards:
            guard_result = guard(self._current_state, to_state)
            if guard_result.is_err():
                return Result.err(guard_result.unwrap_err())

        self._current_state = to_state
        return Result.ok(to_state)

    def force_error_state(self) -> None:
        self._current_state = MaicoState.ERROR
