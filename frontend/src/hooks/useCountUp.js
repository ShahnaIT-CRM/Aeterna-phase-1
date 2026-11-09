import { useEffect, useRef, useState } from 'react'

const easeOutExpo = (t) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t))

/**
 * Counts from 0 to `target` once the referenced element scrolls into view.
 *
 *   const [ref, value] = useCountUp(1.2, { decimals: 1 })
 *   <span ref={ref}>{value}K+</span>
 *
 * - Runs once (the observer disconnects after the first intersection).
 * - Respects prefers-reduced-motion by jumping straight to the target.
 * - Returns the value as a string already formatted to `decimals` places.
 */
export default function useCountUp(target, { duration = 2200, decimals = 0, threshold = 0.4 } = {}) {
  const ref = useRef(null)
  const [value, setValue] = useState(0)

  useEffect(() => {
    const el = ref.current
    if (!el) return undefined

    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    if (reduceMotion || !('IntersectionObserver' in window)) {
      setValue(target)
      return undefined
    }

    let raf = 0
    const run = () => {
      const start = performance.now()
      const tick = (now) => {
        const p = Math.min((now - start) / duration, 1)
        setValue(target * easeOutExpo(p))
        if (p < 1) raf = requestAnimationFrame(tick)
      }
      raf = requestAnimationFrame(tick)
    }

    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          io.disconnect()
          run()
        }
      },
      { threshold },
    )
    io.observe(el)

    return () => {
      io.disconnect()
      cancelAnimationFrame(raf)
    }
  }, [target, duration, threshold])

  return [ref, value.toFixed(decimals)]
}
