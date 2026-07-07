package com.aerogaze.app

import android.app.Application

/**
 * Python is NOT started here anymore. It starts lazily on first AeroGaze use
 * (see AeroGaze.ensureStarted), so the app launches fast, doesn't block the main thread
 * on startup, and a Relay-only session never loads the Python runtime at all.
 */
class AeroGazeApp : Application()
