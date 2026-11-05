"""Thermostat setpoint control with hysteresis."""


def celsius_to_fahrenheit(celsius):
    return celsius * 9.0 / 5.0 + 32.0


def fahrenheit_to_celsius(fahrenheit):
    return (fahrenheit - 32.0) * 5.0 / 9.0


def decide_action(current_celsius, setpoint_celsius, hysteresis_celsius):
    """Return 'heat', 'cool', or 'idle'."""
    if current_celsius < setpoint_celsius - hysteresis_celsius:
        return "heat"
    if current_celsius > setpoint_celsius + hysteresis_celsius:
        return "cool"
    return "idle"


def run_cycle(sensor_fahrenheit, setpoint_celsius, hysteresis_celsius):
    current_celsius = fahrenheit_to_celsius(sensor_fahrenheit)
    action = decide_action(
        current_celsius, setpoint_celsius, hysteresis_celsius)
    return {
        "action": action,
        "current_celsius": round(current_celsius, 2),
        "setpoint_celsius": setpoint_celsius,
    }
