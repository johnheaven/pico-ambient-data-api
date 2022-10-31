def device_uuid_string():
    """Gets the device's UUID as a string.
    Thanks to github.com/JH-87/ for finding out how to do get a string from bytes :)

    Returns:
        str: The string representation of the board's UUID
    """
    import binascii, machine
    return binascii.b2a_base64(machine.unique_id()).decode('utf-8').strip('\n')