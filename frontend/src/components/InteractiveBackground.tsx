import { useEffect, useRef } from 'react';

/**
 * 交互式动态背景（Canvas，零依赖）
 *
 * - 柔和渐变光斑缓慢漂浮（动态渐变氛围）
 * - 光标跟随：移动鼠标时出现靛蓝光晕，光斑被明显吸引聚拢，
 *   并与光标之间拉出「星轨」连线
 * - 点击产生扩散波纹（更醒目）
 * - 整体随鼠标做视差偏移
 * - 尊重 prefers-reduced-motion：渲染单帧静态图
 * - 页面隐藏时暂停渲染，DPR 上限 2，保证 60fps
 */

interface Orb {
    x: number;
    y: number;
    vx: number;
    vy: number;
    r: number;
    hue: string;
    a: number;
}

const ORB_COLORS = [
    '79,70,229',   // 靛蓝
    '124,58,237',  // 紫
    '232,168,10',  // 琥珀
    '56,189,248',  // 天蓝
    '244,63,94',   // 玫红（点缀）
];

const CURSOR_GLOW_RADIUS = 180;
const LINK_RADIUS = 240;

export default function InteractiveBackground({ className }: { className?: string }) {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        let width = 0;
        let height = 0;
        let raf = 0;
        let running = true;

        const pointer = { x: -9999, y: -9999, active: false };
        const orbs: Orb[] = [];
        const ripples: { x: number; y: number; r: number; max: number; a: number }[] = [];

        const resize = () => {
            const parent = canvas.parentElement;
            if (!parent) return;
            const dpr = Math.min(window.devicePixelRatio || 1, 2);
            width = parent.clientWidth;
            height = parent.clientHeight;
            canvas.width = Math.max(1, Math.floor(width * dpr));
            canvas.height = Math.max(1, Math.floor(height * dpr));
            canvas.style.width = `${width}px`;
            canvas.style.height = `${height}px`;
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        };

        const initOrbs = () => {
            orbs.length = 0;
            const count = width < 700 ? 5 : 8;
            for (let i = 0; i < count; i++) {
                orbs.push({
                    x: Math.random() * width,
                    y: Math.random() * height,
                    vx: (Math.random() - 0.5) * 0.32,
                    vy: (Math.random() - 0.5) * 0.32,
                    r: 100 + Math.random() * 160,
                    hue: ORB_COLORS[i % ORB_COLORS.length],
                    a: 0.14 + Math.random() * 0.12,
                });
            }
        };

        const drawOrb = (o: Orb, ox: number, oy: number) => {
            const x = o.x + ox;
            const y = o.y + oy;
            const g = ctx.createRadialGradient(x, y, 0, x, y, o.r);
            g.addColorStop(0, `rgba(${o.hue},${o.a})`);
            g.addColorStop(1, `rgba(${o.hue},0)`);
            ctx.fillStyle = g;
            ctx.beginPath();
            ctx.arc(x, y, o.r, 0, Math.PI * 2);
            ctx.fill();
        };

        const step = () => {
            if (!running) return;
            ctx.clearRect(0, 0, width, height);

            // 视差：整幅画面随鼠标轻微反向移动
            const ox = pointer.active ? (pointer.x / width - 0.5) * -22 : 0;
            const oy = pointer.active ? (pointer.y / height - 0.5) * -22 : 0;

            // 1) 光标光晕：跟随鼠标的靛蓝柔光，让交互一眼可见
            if (pointer.active) {
                const g = ctx.createRadialGradient(pointer.x, pointer.y, 0, pointer.x, pointer.y, CURSOR_GLOW_RADIUS);
                g.addColorStop(0, 'rgba(79,70,229,0.22)');
                g.addColorStop(0.6, 'rgba(124,58,237,0.10)');
                g.addColorStop(1, 'rgba(79,70,229,0)');
                ctx.fillStyle = g;
                ctx.fillRect(pointer.x - CURSOR_GLOW_RADIUS, pointer.y - CURSOR_GLOW_RADIUS, CURSOR_GLOW_RADIUS * 2, CURSOR_GLOW_RADIUS * 2);
            }

            // 2) 星轨连线：光标与附近光斑拉出细线，距离越近越亮
            if (pointer.active) {
                ctx.lineWidth = 1.2;
                for (const o of orbs) {
                    const px = o.x + ox;
                    const py = o.y + oy;
                    const d = Math.hypot(pointer.x - px, pointer.y - py);
                    if (d < LINK_RADIUS) {
                        ctx.strokeStyle = `rgba(79,70,229,${((1 - d / LINK_RADIUS) * 0.5).toFixed(3)})`;
                        ctx.beginPath();
                        ctx.moveTo(pointer.x, pointer.y);
                        ctx.lineTo(px, py);
                        ctx.stroke();
                    }
                }
            }

            // 3) 光斑运动 + 鼠标强吸引
            for (const o of orbs) {
                if (pointer.active) {
                    const dx = pointer.x - o.x;
                    const dy = pointer.y - o.y;
                    const d = Math.hypot(dx, dy) || 1;
                    if (d < 420) {
                        const f = (1 - d / 420) * 0.15;
                        o.vx += (dx / d) * f;
                        o.vy += (dy / d) * f;
                    }
                }
                o.vx *= 0.982;
                o.vy *= 0.982;
                o.x += o.vx;
                o.y += o.vy;

                // 边界软反弹
                if (o.x < -o.r) { o.x = width + o.r; }
                if (o.x > width + o.r) { o.x = -o.r; }
                if (o.y < -o.r) { o.y = height + o.r; }
                if (o.y > height + o.r) { o.y = -o.r; }

                drawOrb(o, ox, oy);
            }

            // 4) 点击波纹：扩散圆环 + 内部柔光
            for (let i = ripples.length - 1; i >= 0; i--) {
                const rp = ripples[i];
                rp.r += 4.2;
                rp.a *= 0.92;
                if (rp.a < 0.015 || rp.r > rp.max) {
                    ripples.splice(i, 1);
                    continue;
                }
                const x = rp.x + ox;
                const y = rp.y + oy;
                // 内部柔光
                const g = ctx.createRadialGradient(x, y, 0, x, y, rp.r);
                g.addColorStop(0, `rgba(79,70,229,${(rp.a * 0.35).toFixed(3)})`);
                g.addColorStop(1, 'rgba(79,70,229,0)');
                ctx.fillStyle = g;
                ctx.beginPath();
                ctx.arc(x, y, rp.r, 0, Math.PI * 2);
                ctx.fill();
                // 外圈
                ctx.strokeStyle = `rgba(124,58,237,${rp.a.toFixed(3)})`;
                ctx.lineWidth = 2.4;
                ctx.beginPath();
                ctx.arc(x, y, rp.r, 0, Math.PI * 2);
                ctx.stroke();
            }

            raf = requestAnimationFrame(step);
        };

        const onPointerMove = (e: PointerEvent) => {
            const rect = canvas.getBoundingClientRect();
            pointer.x = e.clientX - rect.left;
            pointer.y = e.clientY - rect.top;
            pointer.active = true;
        };
        const onPointerLeave = () => {
            pointer.active = false;
        };
        const onPointerDown = (e: PointerEvent) => {
            if (reduce) return;
            const rect = canvas.getBoundingClientRect();
            ripples.push({
                x: e.clientX - rect.left,
                y: e.clientY - rect.top,
                r: 0,
                max: 120 + Math.random() * 80,
                a: 0.8,
            });
        };
        const onVisibility = () => {
            running = document.visibilityState === 'visible';
            if (running && !reduce) {
                cancelAnimationFrame(raf);
                raf = requestAnimationFrame(step);
            }
        };

        const onResize = () => {
            resize();
            if (reduce) {
                ctx.clearRect(0, 0, width, height);
                for (const o of orbs) drawOrb(o, 0, 0);
            }
        };

        resize();
        initOrbs();

        if (reduce) {
            for (const o of orbs) drawOrb(o, 0, 0);
        } else {
            raf = requestAnimationFrame(step);
        }

        window.addEventListener('resize', onResize);
        window.addEventListener('pointermove', onPointerMove);
        window.addEventListener('pointerdown', onPointerDown);
        document.addEventListener('visibilitychange', onVisibility);

        return () => {
            cancelAnimationFrame(raf);
            window.removeEventListener('resize', onResize);
            window.removeEventListener('pointermove', onPointerMove);
            window.removeEventListener('pointerdown', onPointerDown);
            document.removeEventListener('visibilitychange', onVisibility);
        };
    }, []);

    return <canvas ref={canvasRef} className={className} aria-hidden="true" />;
}
