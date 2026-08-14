/**
 * 全局动效增强（零依赖，纯 JS + CSS）
 *
 * - 点击涟漪（Ripple）：所有 antd 按钮按下时从点击处扩散波纹
 * - 磁性悬停（Magnetic Hover）：[data-magnetic] 元素向光标轻微吸附
 * - 3D 倾斜（Tilt）：[data-tilt] 元素跟随光标做 3D 旋转
 *
 * 尊重 prefers-reduced-motion：减少动效时全部禁用。
 */

const prefersReduced = () =>
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const bound = new WeakSet<Element>();

/* ---------- 点击涟漪 ---------- */
function bindRipple() {
    document.addEventListener('pointerdown', (e) => {
        if (prefersReduced()) return;
        const target = e.target as HTMLElement;
        const btn = target.closest?.('.ant-btn') as HTMLElement | null;
        if (!btn) return;
        if ((btn as HTMLButtonElement).disabled) return;
        if (btn.classList.contains('ant-btn-link') || btn.classList.contains('ant-btn-text')) return;
        const rect = btn.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height) * 2.1;
        const span = document.createElement('span');
        span.className = 'dd-ripple';
        span.style.width = `${size}px`;
        span.style.height = `${size}px`;
        span.style.left = `${e.clientX - rect.left - size / 2}px`;
        span.style.top = `${e.clientY - rect.top - size / 2}px`;
        btn.appendChild(span);
        span.addEventListener('animationend', () => span.remove());
    });
}

/* ---------- 磁性悬停 ---------- */
function bindMagnetic(el: HTMLElement, strength = 0.3) {
    if (bound.has(el) || prefersReduced()) return;
    bound.add(el);
    let raf = 0;
    let tx = 0;
    let ty = 0;

    const apply = () => {
        raf = 0;
        el.style.transform = `translate(${tx.toFixed(1)}px, ${ty.toFixed(1)}px)`;
    };
    const onMove = (e: PointerEvent) => {
        const rect = el.getBoundingClientRect();
        tx = (e.clientX - rect.left - rect.width / 2) * strength;
        ty = (e.clientY - rect.top - rect.height / 2) * strength;
        // 限制偏移量，避免宽按钮位移过大
        tx = Math.max(-12, Math.min(12, tx));
        ty = Math.max(-12, Math.min(12, ty));
        el.style.transition = 'transform 0.1s linear';
        if (!raf) raf = requestAnimationFrame(apply);
    };
    const onLeave = () => {
        if (raf) cancelAnimationFrame(raf);
        el.style.transition = 'transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)';
        el.style.transform = 'translate(0, 0)';
    };
    el.addEventListener('pointermove', onMove);
    el.addEventListener('pointerleave', onLeave);
}

/* ---------- 3D 倾斜 ---------- */
function bindTilt(el: HTMLElement, maxDeg = 6) {
    if (bound.has(el) || prefersReduced()) return;
    bound.add(el);
    const onMove = (e: PointerEvent) => {
        const rect = el.getBoundingClientRect();
        const px = (e.clientX - rect.left) / rect.width - 0.5;
        const py = (e.clientY - rect.top) / rect.height - 0.5;
        el.style.transition = 'transform 0.12s ease-out';
        el.style.transform = `perspective(760px) rotateX(${(-py * maxDeg).toFixed(2)}deg) rotateY(${(px * maxDeg).toFixed(2)}deg) translateY(-2px)`;
    };
    const onLeave = () => {
        el.style.transition = 'transform 0.55s cubic-bezier(0.34, 1.56, 0.64, 1)';
        el.style.transform = 'perspective(760px) rotateX(0deg) rotateY(0deg) translateY(0)';
    };
    el.addEventListener('pointermove', onMove);
    el.addEventListener('pointerleave', onLeave);
}

/* ---------- 扫描绑定（含动态插入的元素） ---------- */
function scan() {
    document.querySelectorAll<HTMLElement>('[data-magnetic]').forEach((el) => bindMagnetic(el));
    document.querySelectorAll<HTMLElement>('[data-tilt]').forEach((el) => bindTilt(el));
}

export function initGlobalMotion() {
    if (typeof document === 'undefined') return;
    bindRipple();
    scan();
    const mo = new MutationObserver(scan);
    mo.observe(document.body, { childList: true, subtree: true });
}
