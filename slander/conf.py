DEFAULT_CONFIG = {
    'slack': {
        'token': '',
        },

    'bot': {
        'keepalive_time': 3.,
        'max_cmd_age': 30.,
        'max_errors': 3,
        #'shelve': 'True',
        #'shelve_path': '',
        'sleep_before_reconnect': 1.0,
        'sleep_before_recycle': 20.0,
        'sleep_in_mainloop': 0.1,
        },

    # Channels
    'global': {
        'ignore': '',
        },
    }
