"""더빙 음성 음량을 원본 영어 해설 수준으로 맞춘다: 활성 구간 RMS 맞춤 + 리미터(피크 -0.5dBFS)."""
import numpy as np

def active_rms(x):
    """x: float(-1..1). 20ms 프레임 중 최대보다 30dB 이상 작은 프레임(무음)을 빼고 RMS(dB)"""
    n = 720; f = x[:len(x) // n * n].reshape(-1, n) if len(x) >= n else x.reshape(1, -1)
    e = np.sqrt(np.mean(f ** 2, 1)) + 1e-9; db = 20 * np.log10(e)
    a = f[db > db.max() - 30]
    return 20 * np.log10(np.sqrt(np.mean(a ** 2)) + 1e-9)

def limit(x, lim=0.94, look=72, rel=1440):
    """룩어헤드 피크 리미터(numpy). x: float"""
    from scipy.ndimage import maximum_filter1d, uniform_filter1d
    need = np.minimum(1.0, lim / (np.abs(x) + 1e-12))
    g = -maximum_filter1d(-need, size=2 * look + 1)          # 주변 최소 이득(앞뒤로 미리 낮춤)
    g = uniform_filter1d(g, size=look) if len(g) > look else g  # 부드럽게
    g = -maximum_filter1d(-g, size=look)
    out = -maximum_filter1d(-g, size=rel // 4)  # 짧게 유지한 뒤
    out = np.minimum(g, uniform_filter1d(out, size=rel // 4))  # 부드럽게 복귀
    return x * out

def match(pcm, target_db):
    """pcm s16le bytes -> 활성 RMS가 target_db가 되도록 키우고 리미터"""
    x = np.frombuffer(pcm, '<i2').astype(np.float64) / 32768
    if not len(x) or np.abs(x).max() < 1e-4: return pcm
    for _ in range(3):
        g = target_db - active_rms(x)
        if abs(g) < 0.3: break
        x = limit(x * 10 ** (g / 20))
    return (np.clip(x, -1, 32767 / 32768) * 32768).round().astype('<i2').tobytes()
