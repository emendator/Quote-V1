import { useEffect, useRef, useState } from 'react';

/**
 * 数字滚动（Count-up）：从当前值平滑滚动到目标值。
 * 尊重 prefers-reduced-motion：直接跳到目标值。
 */
export function useCountUp(target: number, duration = 750): number {
    const [value, setValue] = useState(0);
    const fromRef = useRef(0);
    const rafRef = useRef(0);

    useEffect(() => {
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            fromRef.current = target;
            setValue(target);
            return;
        }
        const from = fromRef.current;
        if (from === target) return;
        const start = performance.now();
        const tick = (now: number) => {
            const p = Math.min(1, (now - start) / duration);
            const eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
            const v = from + (target - from) * eased;
            setValue(v);
            if (p < 1) {
                rafRef.current = requestAnimationFrame(tick);
            } else {
                fromRef.current = target;
            }
        };
        rafRef.current = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(rafRef.current);
    }, [target, duration]);

    return value;
}

/** 便捷组件：¥ 金额滚动 */
export function CountUpMoney({ value, fontSize = 14, strong = false }: { value: number; fontSize?: number; strong?: boolean }) {
    const v = useCountUp(value);
    return (
        <span className={strong ? 'dd-amount' : undefined} style={{ fontFamily: 'var(--font-mono)', fontVariantNumeric: 'tabular-nums', fontSize }}>
            ¥{v.toFixed(2)}
        </span>
    );
}
