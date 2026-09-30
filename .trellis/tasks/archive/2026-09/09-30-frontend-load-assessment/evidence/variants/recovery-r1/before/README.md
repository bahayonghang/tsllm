# 隔离方案与构建证据

日期：2026-09-30（America/Chicago）。固定提交：e9ce26a7bd1a4ed67cd30d257354e7345c44dec1。主工作区产品文件未修改。三个方案复用同一批已安装包，未下载或安装依赖。

## 方案边界

| 方案 | 临时改动 | 维护及首次使用代价 |
| --- | --- | --- |
| B0 | 原加载实现，增加路由验证测试和共同构建元数据钩子 | 基线 |
| B1 | 7 条路由均使用 React Router lazy；保留静态 AppLayout，增加初始/导航加载状态和失败后的整页重载链接 | 首次路由访问需要取得对应模块；增加加载及失败处理 |
| B2 | B1 加条件触发的 RunConfigForm、ForecastResults、ClassifyResults、CompareBarChart、SeriesChart、SegmentTimeline | 表单和实际结果满足原展示条件后请求模块；增加 Suspense 和错误边界，可能增加串行等待和请求数 |

B2 保留 RunNewPage 的同步校验器导入。表单模块延后不等于 AJV 全部延后。B2 保留全部原条件、表单回调、查询参数、API 请求和图表组件。未修改依赖、锁文件、生成契约、2000 kB 阈值、target 或 minify。

模块失败后的恢复方式为整页重载，链接保留 pathname、search 和 hash。单元测试在真实路由模块边界注入待定/拒绝 Promise，恢复阶段重建路由并导入真实页面。功能边界测试使用合成模块；真实表单、图表及浏览器重载仍由主任务的可见验收负责。

## 门槛

pnpm 12 在隔离副本发现缺少安装元数据后尝试执行自动安装准备，并拒绝 .pnpm junction，错误为 workspace hoist directory is not a real directory。该尝试在检查前退出；日志显示锁文件无需更新、Already up to date，没有完成依赖下载。保留 B0 三项 attempt 1 日志。随后根据主会话指示，用已安装 .bin 包装器逐条执行 package.json 的原命令，避免 pnpm 自动安装。没有修改脚本内容或参数。

| 方案 | check | test | build |
| --- | --- | --- | --- |
| B0 | attempt 4，通过 | attempt 3，35 passed | attempt 4，通过 |
| B1 | attempt 2，通过 | attempt 2，38 passed | attempt 2，通过 |
| B2 | attempt 2，通过 | attempt 2，40 passed | attempt 2，通过 |

原 5 个测试文件的 27 项测试保持。B0 增加 7 条直接入口与 1 项跨页导航；B1 另加初始等待、导航等待、模块失败/恢复；B2 另加功能等待及失败/恢复。连续查询参数与动态路由参数均验证。测试环境为 jsdom，图表仍沿用原 Canvas 替身；测试通过不证明浏览器实际 Canvas 渲染。

最终命令保持：biome check . && tsc --noEmit；vitest run；tsc --noEmit && vite build。日志和每次命令、退出码、时间保存在 ../variant-gates。全部首轮失败记录保留：

- B0 attempt 2：公共元数据钩子使用了 Rolldown 类型未声明的 originalLength；删除该读取，仅保留其支持的 renderedLength。测试通过，类型检查及构建失败记录保留。
- B0 check attempt 3：钩子在错误工作目录格式化，采用了不同缩进；在副本 web 目录重新按原 Biome 配置格式化。
- B1/B2 test attempt 1：原生 lazy 的拒绝 Promise 在无数据 loader 的路由中产生空 Outlet。改为 loadRoute 捕获导入失败并返回已加载的错误组件。修正后拒绝/恢复用例通过。
- B1 test attempt 1 另有 2 项默认 1 秒等待超时；该次三个方案并行运行，模块转换占用也位于等待范围。没有提高超时或删除原测试，串行重跑通过。
- 保留 jsdom getComputedStyle 既有提示，以及公共评估配置的 Vite 文件扩展名提示；B0 体积提示保持。

## 静态产物口径

| 方案 | 文件数 | 原始总字节 | 各文件 gzip 字节之和 |
| --- | --- | --- | --- |
| B0 | 2 | 2,420,191 | 776,665 |
| B1 | 21 | 2,430,524 | 796,075 |
| B2 | 39 | 2,442,783 | 810,254 |

以上包含 index.html 与全部输出 JS，不是入口加载集合或 HTTP 传输量。gzip 为 Python 3.14.7 / zlib 1.3.1.zlib-ng、gzip.compress(compresslevel=9, mtime=0)，每个文件单独压缩。B0 JS 恰为 2,419,860 字节、gzip 776,403 字节，SHA-256 与已知基线产物相同：9d4690a2705c2b1e2a906c9933ff9c88ee4fc37ca9cd048f7d6e1fd77fb9853f。

每份 inventory 保存所有资源的字节、gzip 估算、SHA-256、HTML 引用和静态闭包。静态闭包不包含随后触发的 lazy 首路由，实际入口必须取浏览器记录。graph 保存 chunk 的静态/动态引用、入口标识与模块归属。renderedLength 为 Rolldown 元数据，不能按其占比推算 gzip、网络或执行时间。

assessmentGraph.ts 只在 generateBundle 读取结果并把 JSON 写到副本 assessment/，不向 dist 注入文件，不加入浏览器探针。体积记录来自正常生产构建。

## 重现

先将固定提交的已跟踪文件导出到独立 source 目录，保留 web/、.gitignore、.gitattributes；不要复制私有目录或 node_modules。下列脚本参数均指向明确的隔离目录。

```powershell
python setup_variants.py --source <source> --dependencies <installed-web-node_modules> --destination <variants> --variant B0
python setup_variants.py --source <source> --dependencies <installed-web-node_modules> --destination <variants> --variant B1
python setup_variants.py --source <source> --dependencies <installed-web-node_modules> --destination <variants> --variant B2
python run_gates.py --root <variants>/B0 --evidence <gate-evidence>
python run_gates.py --root <variants>/B1 --evidence <gate-evidence>
python run_gates.py --root <variants>/B2 --evidence <gate-evidence>
python record_variants.py --root <assessment-root> --evidence <variant-evidence>
```

setup_variants.py 只接受新目的目录；在 Windows 使用已安装 Python 的 _winapi.CreateJunction 复用包目录。node_modules 顶层、.bin、.vite、.vite-temp 和 .cache 是副本本地路径。请通过 run_gates.py 运行，不对副本执行安装，也不要通过普通 pnpm run/exec 触发其自动安装准备。

补丁以固定 source 为基准，不含公共构建钩子；setup_variants.py 先应用公共配置，再以 core.autocrlf=false、core.eol=lf 应用对应补丁。补丁使用零行上下文，避免补丁文本内的空白上下文行触发新增材料尾空格检查；应用时启用 --unidiff-zero，且在前后逐文件核验 SHA-256。独立重建源码副本逐字节比对通过：B0 51、B1 53、B2 55 个文件完全相同，包含原测试、锁和 API 文件。首次重现受仓库外 Git 全局 CRLF 转换影响，初次不一致记录保留于 reproduction-check-initial.json；修正仅作用于补丁应用命令，最终结果见 reproduction-check.json。

门槛日志只规范化换行、终端尾空白及不必要的临时绝对路径；失败原因、断言、次数、退出码和耗时保留。

## 边界

本子任务未启动服务、未操作浏览器、未运行后端、uv、训练、入库或权重下载；未提交、暂存、归档或创建任务。产物和依赖留在临时目录，任务证据仅包含文本脚本、补丁、图及门槛日志。共享包目录在 pnpm 失败前没有哈希快照；后续修改时间检查及安装元数据时间均未发现该失败后的包写入，不能把该检查表述为事前/事后的全部依赖哈希比较。
