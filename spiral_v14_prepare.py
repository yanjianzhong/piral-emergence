# -*- coding: utf-8 -*-
"""
v14 · 参考侧 Gray-Scott 重新播种 (一次性离线步骤)

为什么需要这一步
-----------------------------------------------------------------------------
旧口径的 A 段噪声底 scatter 是由参考侧 3 个种子两两算出来的, 而它读的是归档里的
**bool 场** (spiral_v13_prepare.py: "源文件本身已是 bool, 直接搬")。实测出两件事,
都推翻了"seed 5/10 是退化场, 所以参考侧要换种"这个原判:

  (1) 归档的 3 个**浮点** u 场其实**都是健康的, 而且几乎相同**。中心 100^2 裁剪
      (与下面 CROP 同一区域) 上: seed 0 mean=0.6417 std=0.2930,
      seed 5 mean=0.6415 std=0.2935, seed 10 mean=0.6412 std=0.2950 ——
      mean 到小数点后三位一致, std 到两位一致。全 128^2 上同样是
      mean≈0.6995/0.6993/0.6992, std≈0.2898/0.2903/0.2920。
      这不是退化, 是同一吸引子上的健康斑图。原因是归档 data_make.py 的初始条件
      u0 是**硬编码**的, np.random.seed(0) / random.seed(seed) 设了却从未被使用。
  (2) 归档的 3 个 bool 场 (旧口径真正用的) 占空比是 0.6378 / 0.9181 / 0.9125,
      互相差 0.28, 且**不是**对应浮点场的任何简单二值化。中心 100^2 上逐格
      一致率: 与 (u>中位数) = 0.5688 / 0.5025 / 0.5041 (即与随机猜测无异),
      与 (v>中位数) = 0.4066 / 0.4919 / 0.4869 (更差), 与 (v>0) ≈ 0.62~0.68,
      与 (u>0.5) ≈ 0.63~0.65。其 100^2 / 300 帧的生成管线**不在归档里**,
      无法复现。这些数字由 archive_provenance() 实测并写入
      data/_v14_cache/archive_provenance.json (归档 442 MB, 不适合在度量流程里
      反复读)。

  结论: "seed 5/10 退化"是归档 bool 管线的产物, 不是 Gray-Scott 系统的性质;
  scatter = 0.4544 因此不是"种子间散布", 它测的是一条来路不明的管线的抖动。

本脚本因此自建一套参考侧种子。方程/参数/盒子/网格/时间步与归档逐字相同,
改的是初始条件, 以及**二值化口径** (见下)。

二值化口径为什么是 v 场而不是 u 场
-----------------------------------------------------------------------------
模型侧 (spiral_metric_v14._model_field + _binarize_median) 实际是把
`v/mean(v) - 1` 按中位数二值化, 等价于 **`v > median(v)`**。要两侧同规则,
参考侧就必须也二值化 **v 场**。_binarize_median 的文档字符串写着
"两侧用同一个规则是必须的", 但代码里参考侧用的是归档 bool_u (u 场、未知阈值),
物理量不同、阈值也不同 —— 这是本版修掉的东西。

与归档的关系 (诚实边界)
-----------------------------------------------------------------------------
  - solve_ETDRK4 / N / L 是归档 data_make.py 的逐行副本, 参数一个数没改。
  - 求解器**保持在同一吸引子上**: 从归档 frame0 出发推进 600 帧, 末帧的径向
    谱峰 k=0.0744 (λ=24.18 格) 与归档逐位相同, mean/std 差 ~1%, 直方图吻合。
  - 但它**不能逐位复现** gray_scott_0.npz: 一步映射就差 2.77e-03 (误差集中在
    初始斑点的足迹上), 600 帧后被 Gray-Scott 的混沌放大到 0.73。差异来源是
    **初态**而非动力学 (归档的 IC 不可复现), 但这一点无法从归档单独证明。
  - 归档里 bool 场是 100^2 而浮点场是 128^2, 其 100^2 管线不在归档中。本脚本取
    128^2 的**中心 100x100 裁剪**与该约定对齐 —— 这是**推断**, 不是复现。

产物 (data/_v14_cache/gs_seeds.npz):
  bool_<seed>   bool  (TAIL, 100, 100)  v 场尾窗二值化 (v > 每帧中位数, 同模型侧)
  u_<seed>      f32   (TAIL, 100, 100)  u 场尾窗 (健康判据 + 溯源, 不参与描述子)
  v_<seed>      f32   (100, 100)        末帧浮点 v 场 (诊断)
  meta          JSON 字符串

另出一个小文件 data/_v14_cache/archive_provenance.json: 上面 (1)(2) 两条
   证据的**实测数字** (浮点场统计量、bool 占空比、bool 与各二值化的一致率)。
   归档 442 MB, 度量流程不该做这么大的 I/O, 所以在这里量一次落盘。

只读源: data/gray_scott_data.tar.gz
"""
import os
import json
import time
import tarfile

import numpy as np
from numpy.fft import fftfreq, fft2, ifft2

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
CACHE = os.path.join(DATA, '_v14_cache')

SOURCE_TAR = 'gray_scott_data.tar.gz'

# --- 与归档 data_make.py 逐字相同的物理参数 (一个数都没改) ---
PHY_SIZE = 200 * np.sqrt(5.0)
MESH = 128
DT = 1
TSPAN = (0, 600 + 2 * 1)
DIFFU, DIFFV = 1.0, 0.5
F_PARAM, K_PARAM = 0.01, 0.042

# --- v14 新增 ---
TAIL = 100            # 只保留末尾 TAIL 帧 (稳态斑图)
CROP = 100            # 中心裁剪, 与归档 bool 场的 100^2 约定对齐
MIN_U_STD = 0.15      # 健康判据: **连续** u 场的标准差。死场实测 std~0.04,
                      # 活斑图实测 std~0.29。判据必须落在连续场上 —— 对二值场
                      # 数占空比是恒等式 (按中位数二值化必然给出恰好 50%), 没有信息。
SEED_START = 0
SEED_MAX = 40         # 最多试到这么多号, 凑够 n_target 个健康种子就停

# 归档 gray_scott_data.tar.gz 里实际存在的种子号 (旧口径参考侧用的就是这三个)
SEEDS_IN_ARCHIVE = (0, 5, 10)


def _log(msg):
    print(msg, flush=True)


# ===========================================================================
# 求解器: 归档 data_make.py 的逐行副本 (去掉 tqdm, 其余一字未改)
# ===========================================================================
def solve_ETDRK4(L, N, v0, tspan, dt, output_func):
    """ETDRK4 method"""
    E = np.exp(dt * L)
    E2 = np.exp(dt * L / 2.0)

    contour_radius = 1
    M = 16
    r = contour_radius * np.exp(1j * np.pi * (np.arange(1, M + 1) - 0.5) / M)

    LR = dt * L
    LR = np.expand_dims(LR, axis=-1) + r

    Q = dt * np.real(np.mean((np.exp(LR / 2.0) - 1) / LR, axis=-1))
    f1 = dt * np.real(
        np.mean(
            (-4.0 - LR + np.exp(LR) * (4.0 - 3.0 * LR + LR ** 2)) / LR ** 3, axis=-1
        )
    )
    f2 = dt * np.real(np.mean((2.0 + LR + np.exp(LR) * (-2.0 + LR)) / LR ** 3, axis=-1))
    f3 = dt * np.real(
        np.mean(
            (-4.0 - 3.0 * LR - LR ** 2 + np.exp(LR) * (4.0 - LR)) / LR ** 3, axis=-1
        )
    )

    u = []
    v = v0
    for _t in np.arange(tspan[0], tspan[1], dt):
        u.append(output_func(v))

        Nv = N(v)
        a = E2 * v + Q * Nv
        Na = N(a)
        b = E2 * v + Q * Na
        Nb = N(b)
        c = E2 * a + Q * (2.0 * Nb - Nv)
        Nc = N(c)
        v = E * v + Nv * f1 + 2.0 * (Na + Nb) * f2 + Nc * f3

    return np.stack(u)


def _place_spot(u0, axis, r0, c0, ramp_len, side):
    """归档斑点的机制: 一条 v=1 的窄带 + 紧邻它的 u 斜坡, 斜坡离 v 带越远 u 越高。

    归档原来是在 center 附近手放 6 个这种斑点。这里只把位置/长度/朝向随机化,
    机制不变 —— 关键就是**最低的 u (0.25) 必须紧贴 v 带**, 否则不成核。
    """
    n = MESH
    bands = ((0.25, 2), (0.5, 2), (0.75, 2))     # (u 值, 厚度) 由近及远
    off = 0
    for val, wid in bands:
        a0 = (c0 + side * (2 + off)) if side > 0 else (c0 - off - wid)
        off += wid
        if not (0 <= a0 < n) or not (0 <= a0 + wid <= n):
            continue
        sl = [slice(None)] * 2
        sl[1 - axis] = slice(a0, a0 + wid)
        u0[(0,) + tuple(sl)][r0:r0 + ramp_len] = val
    # v 带: 紧贴最低 u 带 (0.25) 的外侧, 厚 2 格。两侧朝向下都取 [c0, c0+2),
    # 因为上面 side<0 的 0.25 带正是落在 [c0-2, c0)。
    a0 = c0
    if 0 <= a0 < n and 0 <= a0 + 2 <= n:
        sl = [slice(None)] * 2
        sl[1 - axis] = slice(a0, a0 + 2)
        u0[(1,) + tuple(sl)][r0:r0 + ramp_len] = 1.0


def _initial_field(seed):
    """
    按 seed 随机的初始条件 —— 本脚本相对归档的**唯一**物理改动。

    归档的 u0 是硬编码的 6 个斑点, 且它的 np.random.seed 是死代码, 所以
    gray_scott_0/5/10 三个文件其实是同一个 IC 出来的场 (实测三者统计量一致到
    1e-3), 参考侧根本没有"种子间散布"可言。这里把斑点随机化, 才第一次真的
    有了 3 个以上互相独立的参考场。
    """
    rng = np.random.default_rng(seed)
    u0 = np.zeros((2, MESH, MESH), dtype=np.float64)
    u0[0, ...] = 1.0                    # u 背景 = 1
    n_spot = int(rng.integers(4, 9))
    for _ in range(n_spot):
        axis = int(rng.integers(0, 2))
        ramp_len = int(rng.integers(20, 61))
        span = MESH - ramp_len - 12
        r0 = int(rng.integers(0, max(span, 1)))
        c0 = int(rng.integers(8, MESH - 8))
        side = 1 if rng.integers(0, 2) else -1
        _place_spot(u0, axis, r0, c0, ramp_len, side)
    return u0, {'n_spot': n_spot}


def _make_solver():
    """构造与归档 grayscottdataset 内部完全相同的 K 空间算子与非线性项。"""
    kx = np.expand_dims(2 * np.pi * fftfreq(MESH, d=PHY_SIZE / MESH), axis=-1)
    ky = np.expand_dims(2 * np.pi * fftfreq(MESH, d=PHY_SIZE / MESH), axis=0)
    D2 = -(kx ** 2 + ky ** 2)
    L = np.stack((DIFFU * D2, DIFFV * D2))

    def N(v):
        u = np.real(ifft2(v))
        u1 = u[..., 0, :, :]
        u2 = u[..., 1, :, :]
        du = np.stack([-1 * u1 * u2 ** 2 + F_PARAM * (1 - u1),
                       1 * u1 * u2 ** 2 - (F_PARAM + K_PARAM) * u2], axis=-3)
        return fft2(du)

    return L, N


def gs_run(seed):
    """跑一个种子, 返回 (bool 尾窗 (TAIL,100,100), u 尾窗 f32, 末帧 v f32)。"""
    u0, ic_meta = _initial_field(seed)
    L, N = _make_solver()
    c = (MESH - CROP) // 2

    def grab(v):
        uv = np.real(ifft2(v))                       # (2,128,128)
        return uv[:, c:c + CROP, c:c + CROP].astype(np.float32)

    sol = solve_ETDRK4(L, N, fft2(u0), TSPAN, DT, grab)   # (n,2,100,100) f32
    tail = sol[-TAIL:]
    u_tail, v_tail = tail[:, 0], tail[:, 1]
    # v > 每帧自己的中位数 —— 与模型侧的 _model_field + _binarize_median 同规则
    b = v_tail > np.median(v_tail, axis=(1, 2), keepdims=True)
    return b, u_tail, v_tail[-1], ic_meta


def archive_provenance(force=False):
    """
    量出"归档 bool 场到底是什么" —— 这是参考侧必须换掉的**证据**, 不是推测。

    归档 442 MB, 逐成员解压一次约一分钟, 所以结果落成一个小 JSON
    (data/_v14_cache/archive_provenance.json), 由 metric 侧读取, 避免在度量
    流程里做 442 MB 的 I/O。可重复: 删掉 JSON 再跑本函数即可复算。

    量三件事:
      (1) 三个浮点场的 u 统计量 —— 若三者几乎相同, 说明它们是同一个 IC;
      (2) 归档 bool 场 (旧口径真正用的) 的占空比;
      (3) bool 场与同一归档浮点场各种简单二值化的一致率 —— 若都在 0.5 附近,
          说明 bool 场的生成管线不在归档里, 无法复现。
    """
    out = os.path.join(CACHE, 'archive_provenance.json')
    if os.path.exists(out) and not force:
        _log(f"  [溯源] 已存在, 跳过 ({out})")
        return True
    src = os.path.join(DATA, SOURCE_TAR)
    if not os.path.exists(src):
        _log(f"  [溯源] 缺少 {src}, 跳过 (参考侧仍可自建, 但缺口无法量化)")
        return False

    import io as _io
    rec = {'source': SOURCE_TAR, 'seeds': [], 'clip_offset': (MESH - CROP) // 2}
    with tarfile.open(src, 'r:gz') as tf:
        mem = {m.name.split('/')[-1]: m for m in tf.getmembers() if m.isfile()}
        rec['members'] = sorted(mem)
        c = (MESH - CROP) // 2
        for s in SEEDS_IN_ARCHIVE:
            fs, bs = f'gray_scott_{s}.npz', f'gray_scott_bool_{s}.npz'
            if fs not in mem or bs not in mem:
                continue
            sol = np.load(_io.BytesIO(tf.extractfile(mem[fs]).read()))['sol']
            ub = np.load(_io.BytesIO(tf.extractfile(mem[bs]).read()))['bool_u']
            b = np.asarray(ub[-1] if ub.ndim == 3 else ub, dtype=bool)
            uf = sol[-1, 0]
            vf = sol[-1, 1]
            uc, vc = uf[c:c + CROP, c:c + CROP], vf[c:c + CROP, c:c + CROP]
            rec['seeds'].append({
                'seed': int(s),
                'float_u_mean': float(uf.mean()), 'float_u_std': float(uf.std()),
                'float_u_std_c': float(uc.std()), 'float_v_std_c': float(vc.std()),
                'bool_fill': float(b.mean()),
                'agree_u_med': float(np.mean(b == (uc > np.median(uc)))),
                'agree_v_med': float(np.mean(b == (vc > np.median(vc)))),
                'agree_v_gt0': float(np.mean(b == (vc > 0))),
                'agree_u_gt_half': float(np.mean(b == (uc > 0.5)))})
            _log(f"    seed {s}: float_u mean={uf.mean():.4f} std={uf.std():.4f} | "
                 f"bool 占空比={b.mean():.4f} | 一致率 u>med="
                 f"{rec['seeds'][-1]['agree_u_med']:.4f} v>med="
                 f"{rec['seeds'][-1]['agree_v_med']:.4f}")
    rec['note'] = ('归档 bool 场 (v13 参考侧直接搬的) 与同目录浮点场的任何简单'
                   '二值化一致率都在 0.5 附近 -> 其生成管线不在归档中, 不可复现; '
                   '且三个浮点场统计量几乎相同 -> 归档 data_make.py 的 IC 硬编码, '
                   '其 np.random.seed/random.seed 是死代码, 三个"种子"同出一个 IC。')
    os.makedirs(CACHE, exist_ok=True)
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=1)
    _log(f"  [溯源] 写出 {out}")
    return True


def prep_gs_seeds(n_target=12, force=False):
    out = os.path.join(CACHE, 'gs_seeds.npz')
    if os.path.exists(out) and not force:
        _log(f"  [gs_seeds] 已存在, 跳过 ({os.path.getsize(out)/1048576:.1f} MB)")
        archive_provenance()
        return True

    _log(f"  [gs_seeds] 溯源: 归档 {SOURCE_TAR}")
    archive_provenance(force)

    t0 = time.time()
    payload, health, rejected = {}, {}, []
    for seed in range(SEED_START, SEED_MAX):
        if len(health) >= n_target:
            break
        t1 = time.time()
        b, u_tail, v_last, ic = gs_run(seed)
        u_std = float(u_tail[-1].std())
        ok = u_std >= MIN_U_STD
        _log(f"    seed {seed:>2}: 连续 u 场 std={u_std:.4f} (末帧占空比 "
             f"{float(b[-1].mean()):.4f} 为恒等式, 仅记录)  "
             f"({ic['n_spot']} 个初始斑点, {time.time()-t1:.0f}s)  "
             f"-> {'采用' if ok else '**剔除** (未成核/死场)'}")
        if not ok:
            rejected.append({'seed': seed, 'u_std': u_std})
            continue
        payload[f'bool_{seed}'] = b
        payload[f'u_{seed}'] = u_tail
        payload[f'v_{seed}'] = v_last
        health[str(seed)] = {'u_std': u_std, 'u_mean': float(u_tail[-1].mean())}

    n_full = len(np.arange(TSPAN[0], TSPAN[1], DT))
    meta = {'source': SOURCE_TAR,
            'solver': 'ETDRK4 (归档 data_make.py 的逐行副本)',
            'params': {'diffu': DIFFU, 'diffv': DIFFV, 'f': F_PARAM, 'k': K_PARAM,
                       'mesh': MESH, 'phy_size': float(PHY_SIZE), 'dt': DT,
                       'tspan': list(TSPAN), 'n_frames_full': n_full},
            'tail': TAIL, 'crop': CROP, 'crop_offset': (MESH - CROP) // 2,
            'binarize': 'v > 每帧中位数 (与模型侧 _model_field+_binarize_median 同规则)',
            'health_metric': f'连续 u 场 std >= {MIN_U_STD}',
            'seeds': sorted(int(k.split('_')[1]) for k in payload
                            if k.startswith('bool_')),
            'rejected': rejected, 'health': health,
            'note': ('v14 自建种子。方程/参数/盒子/网格/时间步与归档 data_make.py '
                     '逐字相同, 唯一改动是初始条件按 seed 随机。归档的 IC 是硬编码的, '
                     '其 seed 0/5/10 实为同一个 IC, 且归档 bool 场与归档浮点场对不上 '
                     '(一致率仅 50~65%), 故参考侧无法从归档复现, 只能自建。'
                     '中心裁剪到 100^2 是为与归档 bool 场的 100^2 约定对齐 —— 该 100^2 '
                     '的生成管线不在归档中, 所以这一步是**推断**而非复现, 必须声明。')}
    payload['meta'] = np.array(json.dumps(meta, ensure_ascii=False))

    os.makedirs(CACHE, exist_ok=True)
    np.savez_compressed(out, **payload)
    _log(f"  [gs_seeds] 写出 {out} ({os.path.getsize(out)/1048576:.1f} MB, "
         f"采用 {len(health)} 个 / 剔除 {len(rejected)} 个, {time.time()-t0:.0f}s)")
    return True


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true', help='已有缓存也重做')
    ap.add_argument('--n', type=int, default=12, help='需要的健康种子数')
    args = ap.parse_args()

    os.makedirs(CACHE, exist_ok=True)
    print("=" * 74)
    print(f"v14 · 参考侧 Gray-Scott 重新播种 -> {CACHE}")
    print("=" * 74)
    print(f"  参数 (与归档逐字相同): f={F_PARAM}, k={K_PARAM}, mesh={MESH}, "
          f"phy_size={PHY_SIZE:.2f}, dt={DT}, tspan={TSPAN}")
    print(f"  健康判据: 连续 u 场 std >= {MIN_U_STD}")
    prep_gs_seeds(args.n, args.force)
    print("\n下一步: python spiral_model_v14.py")


if __name__ == '__main__':
    main()
