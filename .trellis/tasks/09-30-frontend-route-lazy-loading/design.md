# B1 路由加载设计

## 基线与边界

实测 HEAD 为 `e9ce26a7bd1a4ed67cd30d257354e7345c44dec1`，初始分支 `codex/frontend-load-assessment`；产品相对指定基线无差异。原未跟踪文件仅属于旧评估任务。已按明确授权创建唯一新任务和 `codex/frontend-route-lazy-loading`，未覆盖同名目标。没有发现嵌套 AGENTS.md 或 CONTEXT.md。父任务共享契约只读。

行为差距在路由定义及加载反馈层。七个静态页面导入使表单/图表依赖进入列表入口。使用 React Router 的路由 lazy 导入各页面，返回现有命名页面组件。同步 AppLayout 继续拥有菜单和 Outlet；初始 HydrateFallback 与 useNavigation 导航状态显示统一中文加载组件。

## 加载和错误契约

保留原 routes 层级及根 Navigate replace 行为。路由加载包装仅捕获动态导入失败，返回同步错误组件；必要路由错误边界使用同一呈现。恢复入口 href 为当前 pathname+search+hash；点击 preventDefault 后调用 globalThis.location.reload()。不承诺当前文档内重试，jsdom 替身只证明调用；真实浏览器验证新的文档时间源、navigation reload、完整地址和真实图表。

按当前源代码逐项迁移最小 B1 改动。参考 patch 不自动应用；不引入 B2、评估插件、探针或夹具到产品。原有 API、数据及图表文件保持哈希不变。

## 隔离验收与版本绑定

从固定 Git 基线导出已跟踪必要源文件到新任务拥有的隔离执行目录；只复制显式产品文件，不复制私有根目录。B0 保留基线；B1 覆盖最终 web 源码。使用原 package/config/锁文件与已安装依赖，不安装。完整门槛在独立副本执行，输出写其 dist，主工作区旧 dist 保持。冻结源码、工具和 dist 清单 SHA-256；性能与可见验收共用同一正式 B1。所有隔离产物、工具与日志仅在新任务范围内。

合成夹具从旧任务可追溯生成器重新生成；显式设置全部 configs/cache/runs/model-cache 路径，只有终态作业。前后记录哈希、大小和 mtime；不执行入库或真实 worker。只有一个自有服务占用 127.0.0.1:9000，切换方案时先确认退出；占用冲突停止。

## 性能方法

复制并溯源 recovery-r1 instrument/after 的采集逻辑到任务 tools。保留就绪判定、两次稳定帧、图表数值/像素检查、原始资源/longTasks/navigation、paintAtReady，以及最长 1000 ms 的后补原生 FCP。只适配两方案、产物路径及版本/空目录保护。B0/B1 逐轮交替，各 cold-runs、warm-runs、first-form、first-compare、first-dataset、first-forecast 五次；单独完整旅程各一次。每条记录绑定工具和正式产物版本；拒绝非空无 sidecar、混版或覆盖。

独立复算以原始记录与冻结资产为输入。就绪中位数及完整范围、累计 URL 并集、资源 body/transfer、文档/API 开销、逐文件 gzip 估算分别报告。较高值保持有效，失败保留并解释。单旅程时间不推论稳定性。只说明本机浏览器、合成夹具、环回网络结果。

## 派发和回退

已核对 workflow 2.1/2.2 及 .codex/agents profiles。每次派发首行使用 task.py current 的实际路径。优先检查 native trellis-hook-injected / saved output；缺失按 role JSONL → 引用材料 → prd → design → implement 加载。禁止子代理递归派发。产品实施代理独占允许的产品路径；验收工具代理仅拥有新任务指定 tools/evidence；主会话协调并操作可见浏览器、更新任务/specs；checker 独立只写 review 证据，发现回灌实施代理。各代理共享工作区，不撤销他人改动。

发生产品修复后建立新冻结快照并重跑受影响正式门槛与同条件验收；不能把不同产物数据混合。故障注入只临时移开隔离 dist 模块，用 finally 还原同一字节文件。禁止清理旧任务或私有目录。
