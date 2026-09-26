# 固定床离子交换动态穿透计算服务

面向工业纯水制备软化床的穿透评估后端。给定进料浓度、流量、床层容量、
速率常数与填料质量，服务沿时间轴把出水相对浓度曲线离散地展开，
并从曲线上读出穿透时刻与累计吸附量。仅经 HTTP/JSON 对外提供，
不附带页面，也不生成用水工单。

## 模型

采用 Thomas 解的固定形式：

```
C(t)/C0 = 1 / (1 + exp(kTh * (q0*m/Q - C0*t)))
```

- `C0` 进料浓度（如 mg/L），`Q` 体积流量（如 L/min），`q0` 单位吸附容量
  （如 mg/g），`kTh` Thomas 速率常数（1/(浓度·时间)，如 L/(mg·min)），
  `m` 填料质量（如 g）。
- 指数项 `kTh*(q0*m/Q - C0*t)` 随时间单调减小，曲线从低往高单调爬升；
  半穿透特征时刻为 `t_half = q0*m/(Q*C0)`。
- 穿透时刻：相对浓度首次跨过约定阈值（默认 0.05，可用 `threshold` 覆盖），
  相邻采样点间线性插值。
- 默认时间网格（`t_end` 与 `n_points` 都缺省时）按"前沿加密、两端稀疏"
  分段取样：Thomas 前沿宽度正比于 `1/(kTh*C0)`，与床装量无关，均匀网格
  无法兼顾；加密保证 10%–90% 爬升段内始终有足够采样点，穿透时刻与
  爬升窗口才能从返回曲线上如实读出。
- 累计吸附量：`M(t) = Q*C0 * ∫(1 - C/C0) dt`，标准库手写梯形公式；
  运行足够久时趋近理论容量 `q0*m`。曲线未越过半程（末端相对浓度 < 0.5）
  或累计量未达容量 99% 时，`saturated` 一律为 false。

## 模块划分

| 文件 | 职责 |
| --- | --- |
| `app/thomas.py` | Thomas 解求值（数值稳定、指数符号锁定） |
| `app/timegrid.py` | 时间轴离散（默认网格前沿加密、覆盖到饱和；显式给 `t_end`/`n_points` 时退回均匀网格） |
| `app/integrate.py` | 浓度亏量的梯形积分 |
| `app/breakthrough.py` | 穿透时刻判定与 10%–90% 爬升窗口 |
| `app/validation.py` | 输入校验（五参数必须为正，错误带原因） |
| `app/pipeline.py` | 单工况流程编排 |
| `app/batch.py` | 批量工况调度（逐条独立、错误隔离） |
| `app/presets.py` | 预置软化床参考算例 |
| `app/server.py` | Flask 接口层 |

## API

- `GET  /api/v1/health` 健康检查
- `GET  /api/v1/presets/softening` 预置软化床算例（参数 + 当场算出的曲线）
- `POST /api/v1/breakthrough/run` 单工况：整条曲线 + 穿透时刻 + 累计吸附
- `POST /api/v1/breakthrough/batch` 批量：`{"runs": [工况, ...]}`，逐条独立产出

单工况请求体：

```json
{
  "C0": 150.0, "Q": 2.0, "q0": 40.0, "kTh": 0.002, "m": 5000.0,
  "threshold": 0.05, "t_end": null, "n_points": 400
}
```

`threshold` / `t_end` / `n_points` 均可省略。任一必需参数不为正数时，
返回 400 并在 `error.reasons` 中逐条说明原因。

示例：

```bash
curl -s -X POST http://localhost:8080/api/v1/breakthrough/run \
  -H 'Content-Type: application/json' \
  -d '{"C0":150.0,"Q":2.0,"q0":40.0,"kTh":0.002,"m":5000.0}'
```

## 本地运行与测试

```bash
pip install -r requirements.txt
python run.py            # 服务监听 8080
python -m pytest -q      # 运行全部测试
```

## Docker

```bash
docker build -t breakthrough-service .
docker run --rm -p 8080:8080 breakthrough-service            # 起服务
docker run --rm breakthrough-service python -m pytest -q     # 同一容器内跑测试
```

## 测试锁定的关键规律（tests/test_relations.py）

- 单位吸附容量加倍、其余不变 → 穿透时刻大致推后一倍；
- 体积流量加倍 → 穿透提前到来（大致减半）；
- 速率常数调大 → 10%–90% 爬升窗口收窄、曲线变陡；
- 进料浓度取零 → 带原因的校验错误；
- 运行足够久 → 累计吸附量趋近理论容量 `q0*m`（守恒判据），
  且曲线未越过半程时不得宣称饱和。
