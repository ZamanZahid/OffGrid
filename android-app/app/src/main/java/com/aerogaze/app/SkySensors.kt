package com.aerogaze.app

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager

/**
 * Reads the fused gravity vector around the moment of capture. Average over a short
 * still window for a clean "down" vector -- the single most accuracy-critical input
 * (1 deg tilt ~ 110 km). Also exposes the latest rotation-vector attitude if needed.
 */
class SkySensors(context: Context) : SensorEventListener {

    private val sm = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val gravitySensor: Sensor? = sm.getDefaultSensor(Sensor.TYPE_GRAVITY)
    private val rotationSensor: Sensor? = sm.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR)

    private val gx = ArrayList<Float>()
    private val gy = ArrayList<Float>()
    private val gz = ArrayList<Float>()

    @Volatile
    var latestQuat: FloatArray? = null
        private set

    fun start() {
        gx.clear(); gy.clear(); gz.clear()
        gravitySensor?.let { sm.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME) }
        rotationSensor?.let { sm.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME) }
    }

    fun stop() = sm.unregisterListener(this)

    fun sampleCount(): Int = gx.size

    /** Mean gravity over the captured window, as [x, y, z]. */
    fun averagedGravity(): DoubleArray {
        val n = gx.size.coerceAtLeast(1)
        return doubleArrayOf(
            gx.sum().toDouble() / n,
            gy.sum().toDouble() / n,
            gz.sum().toDouble() / n,
        )
    }

    override fun onSensorChanged(e: SensorEvent) {
        when (e.sensor.type) {
            Sensor.TYPE_GRAVITY -> {
                gx.add(e.values[0]); gy.add(e.values[1]); gz.add(e.values[2])
            }
            Sensor.TYPE_ROTATION_VECTOR -> {
                val q = FloatArray(4)
                SensorManager.getQuaternionFromVector(q, e.values)  // [w, x, y, z]
                latestQuat = q
            }
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}
}
