import json
import os
import tempfile
import time


class NullSmoother:
    def step(self, key, value, t=None):
        return value


class Smoother:
    def __init__(self, logger, halflife, reset_threshold, save_path):
        self._logger = logger
        self._halflife = halflife
        self._reset_threshold = reset_threshold
        self._save_path = save_path

        try:
            with open(save_path) as f:
                self._states = json.load(f)
            _validate_states(self._states)
        except:
            self._states = {}

    def step(self, key, value, t=None):
        if t is None:
            t = time.time()

        value = float(value)
        t = float(t)

        if key in self._states:
            old_value = self._states[key]['value']
            if abs(value - old_value) > self._reset_threshold * old_value:
                self._logger.info(f'Smoother reset key {key} value {value} old_value {old_value}')
                self._states = {}

        if key not in self._states:
            self._states[key] = {
                'value': value,
                't': t,
            }
        else:
            s = self._states[key]
            elapsed = t - s['t']
            alpha = 1 - 0.5 ** (elapsed / self._halflife)
            s['value'] = (1 - alpha) * s['value'] + alpha * value
            s['t'] = t

        if self._save_path is not None:
            with tempfile.TemporaryDirectory() as dir:
                tmp_path = os.path.join(dir, 'states.json')
                with open(tmp_path, 'w') as f:
                    json.dump(self._states, f, indent=4, sort_keys=True)
                os.replace(tmp_path, self._save_path)

        return self._states[key]['value']


def _validate_states(states):
    for key in states:
        assert isinstance(states[key]['value'], float)
        assert isinstance(states[key]['t'], float)
