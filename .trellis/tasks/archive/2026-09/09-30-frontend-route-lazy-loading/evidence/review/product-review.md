# 冻结产品静态初检

检查范围：`web/src/router.tsx`、`web/src/components/AppLayout.tsx`、`web/src/components/RouteLoading.tsx`、`web/tests/LazyRouting.test.tsx`、`web/tests/RouteResolution.test.tsx`。

## Findings (fixed)

无产品修复。检查代理没有写入产品文件。

## Findings (not fixed)

当前静态检查未发现范围内问题。真实文档重载、Canvas、正式隔离构建及性能数据仍由后续同修订证据验证；不将尚未完成的材料列为缺陷。

## 行为与测试检查

| 条件 | 实际机制与断言 | 初检结论 |
| --- | --- | --- |
| 七路由 | 七个路由使用 `loadRoute` 包装动态导入；每个目标为原有命名页面组件。测试逐个核对路由、参数、组件身份。 | 符合 |
| 同步布局 | AppLayout 保持静态导入，菜单与 Outlet 保持。导航等待测试保留平台链接和原运行页。 | 符合 |
| 根重定向 | 原 `Navigate to="/runs" replace` 保持；测试核对 `/runs` 和 `REPLACE`。 | 符合 |
| 地址和历史 | 七入口及跨页导航均保留 pathname/search/hash。测试核对前进和后退的完整参数、片段。 | 符合 |
| 初始等待 | 父路由的 HydrateFallback 使用统一中文 status；deferred import 解决前后分别核对显示和消失。 | 符合 |
| 导航等待 | AppLayout 根据 useNavigation 显示相同 status；测试通过实际菜单点击触发并在模块完成后消失。 | 符合 |
| 模块失败 | loadRoute 捕获导入失败并返回同步中文错误组件；初始和导航失败均有断言。 | 符合 |
| 恢复操作 | href 含 pathname/search/hash；点击取消默认动作并调用 `globalThis.location.reload()`。测试实际点击、核对取消默认动作、reload 一次和 URL 保持，覆盖空及非空 hash。 | jsdom 调用契约符合；真实重载待浏览器证据 |
| 原有业务 | 产品 diff 仅路由导入和导航状态；页面、API、图表、表单与依赖均没有改动。`product-gates.json` 对比 B0/B1 完整源码集合，差异严格为上列五文件。 | 符合 |

## 已有门槛证据

`evidence/implementation/gates/check-3.json` 与 `test-4.json` 退出码为 0。两个记录绑定相同五文件 SHA-256；check 使用原 `biome check .` 与 `tsc --noEmit`，test 使用完整 `vitest run`。当前记录为 41 项测试，其中原有 27 项和新增 14 项。最终隔离 B1 的 check/test/build 另行核对；未重复并行运行门槛干扰验收。

## 正式隔离门槛独立复核

`product-gates.json` 已独立通过，复算脚本为 `audit_product.py`。

- B0 的 51 项 source manifest 与固定提交对应 Git blob 逐字节一致。B1 的 54 项与当前工作区逐字节一致。两方案 source/dist version 由排序后的 SHA-256/长度映射独立复算，均一致。
- B0/B1 唯一差异为三份产品源码及两份新测试。八份原 tests 文件全部保留；依赖、锁文件、API、生成类型、图表与构建配置保持。
- `B0-{check,test,build}-1.json` 与 `B1-r1-{check,test,build}-1.json` 共六个正式门槛均退出 0，每个子命令 argv 与 package.json 完全一致。check 包含 Biome 和 TypeScript，build 包含 TypeScript 和 Vite。
- B0 完整套件为 27 项，B1 为 41 项。独立读取 UTF-8 日志核对计数，没有筛选测试或替代完整门槛。每份 gate JSON、日志和源码指纹均记录于独立结果。
- 已复用相同最终源码的通过证据，没有在性能验收期间重复执行产品门槛。

## 采集工具检查

browser_probe.mjs 与 recovery-r1 的 SHA-256 同为 `3ae70bc5884653d1aeb29dda42c81221af0b4bf64bc1bf43874419d25b9b80dd`。measure.mjs 的 diff 限于两方案参数、路径/版本/产物绑定、非空目录保护和样本元数据；原 sample、就绪与 collectPaint 调用顺序保持。服务明确绑定隔离 configs/cache/runs/model-cache 和最终 dist，检查五个终态作业、空模型缓存及服务未导入 torch。没有启动浏览器或服务进行重复检查。

构建清单首次使用 Node zlib 得到不同 gzip 估算，工具代理已保留初始清单并统一改回 Python 3.14.7 / zlib 1.3.1.zlib-ng 的逐文件 level=9、mtime=0 口径。最终实验清单已记录该版本。独立复算将按相同口径核对每个文件。
