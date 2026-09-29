# shadowrocket-antidad

小火箭（Shadowrocket）反广告模块 · 自持整合版

把三个上游规则源整合成**一个模块、一个链接、一份白名单**，托管在自己的仓库里，链接不依赖第三方模块仓库是否改名、停更或归档。

另附一个 **URL 级整合档**（需要开 HTTPS 解密，不打算开就别装）：

- `antidad-rewrite.module` —— ★ **所有 URL 级去广告一个模块搞定**：App 开屏 + 知乎 + B站 + 微信公众号，**25 个解密目标、0 个 CDN**。见第七节。

**日常只需要两个模块，而且两者不重叠**：

```
antidad-full.module      域名级 · 29.6 万条域名 + 767 条关键词/IP · 0 解密
antidad-rewrite.module   URL 级 · 全部 App 内去广告 · 25 解密 · 不含域名级规则
```

> **分层是这个项目的硬约束**：域名级模块里**只有** `DOMAIN*` / `IP-CIDR` / 规则集引用，
> URL 级模块里**只有** `URL-REGEX` / `[URL Rewrite]` / `[Script]` / `[MITM]`。
> 两个方向都不许越界 —— 由 `scripts/audit_layers.py` 每次构建时强制断言（见第八节）。

> **另附**：`dist/divert.conf` —— 一份**自建分流订阅**（派生自 johnshall 的 `lazy_group.conf`，
> 修掉上游 4 条写错客户端方言的死规则）。它与反广告**无关**，只是同仓托管，见**第十二节**。

---

## 一、解决什么问题

用别人的现成模块有三个隐患：

| 隐患 | 具体表现 |
|---|---|
| 链接不属于自己 | 上游改仓库名 / 改默认分支 / 归档，安装链接就失效，手机上的模块更新不了 |
| 无法定制 | 误杀了某个域名，只能等上游改，或者每换一次配置就手动重加一遍 |
| 来源分散 | 想同时用 blackmatrix7 和 anti-AD，得装两个模块，没有统一入口 |
| **上游会删路径** | 模块引用的上游文件被作者搬走 / 删除后，模块**静默失效**（小火箭不报错，规则一条不生效）|

最后一条是本项目亲历的：`deezertidal/shadowrocket-rules` 的知乎模块引用了 `ios_rule_script/script/zhihu/zhihu_plus.js`，而 blackmatrix7 早把 `script/zhihu/` 整个目录删掉了 —— 那两个文件现在都是 **404**。模块照样安装、照样显示已启用、照样解密流量，但一条规则都没生效。**纯耗电、零收益。**

本仓库的做法：**模块只有几 KB，规则集仍引用上游**。这样既拿到稳定的自有链接和可控白名单，又不用把 5.7 MB 的规则集存进 Git、也不需要每天跑任务去同步。上游规则集本身就是每天自动更新的，引用它比自己搬运更新鲜。

---

## 二、三个域名级档位 + 一个 URL 级整合档（+ 两个子集档）

**推荐组合**：`antidad-full`（域名级）+ `antidad-rewrite`（URL 级）。两个模块就够。

| 类 | 档位 | 模块文件 | 内容 | 解密目标 | 适用 |
|---|---|---|---|---|---|
| 域名级 | **整合版**（推荐） | `antidad-full.module` | anti-AD + blackmatrix7 域名集 + 767 条关键词/IP + 4 条知乎域名/IP，去重后约 29.6 万域名 | **0** | 默认选择。双源互补，覆盖最广 |
| 域名级 | 轻量版 | `antidad-lite.module` | blackmatrix7 AdvertisingLite ×2，约 3.8 万 | **0** | 省流量、少误杀 |
| 域名级 | 严格版 | `antidad-strict.module` | 整合版 + LOWERTOP AntiAD | **0** | ⚠️ 额外拦遥测/推送域，**会误杀**，见第五节 |
| URL 级 | **重写整合**（推荐） | `antidad-rewrite.module` | App开屏 + 知乎 + B站 + 微信公众号，**全部内联**，**不含任何域名级规则** | **25** | ⭐ 主力。所有 URL 级去广告只装这一个 |
| URL 级 | 开屏（子集） | `antidad-splash.module` | 仅 `antidad-rewrite` 里的 App 开屏部分 | 9 | 只要开屏、不碰 B站脚本 |
| 子集 | 知乎 | `antidad-zhihu.module` | 知乎的域名层（4 条）+ URL 层（8 条）全套 | 7 | 只想去知乎广告、解密面要最小 |

**域名级模块的白名单只出现在含域名级黑名单的档里**（积分版 / 轻量版 / 严格版）。
URL 级档位没有任何域名级 `REJECT`，白名单在那里没有放行对象 —— 注进去只会让两个模块出现
逐字重复的同样 3 行，那正是本README要消灭的「重叠」。这条也由 `audit_layers.py` 断言。

**为什么整合版要做双源**（2026-09-28 复测）：anti-AD 102,114 条、blackmatrix7 域名集 285,470 条，
**两者去重后是 295,994 条**。即 anti-AD 的 89.7%（91,590 条）本来就在 blackmatrix7 里，
反过来说 blackmatrix7 只能覆盖 anti-AD 的九成 —— 它是聚合型列表，anti-AD 本就是它的上游之一。
anti-AD 单独贡献 **10,524 条**独有域名。量不大，**但引用成本是零**（`DOMAIN-SET` 一条、不必开 MITM），
所以保留双源。

> ⚠️ 本段此前写的是「交集只有 1,926 条、去重后 382,242 条」——**错的**。
> 那个数把两个有交集的源**直接相加当并集**算，得出的交集自然是假的。实测交集 91,590 条。
> 教训见第 22 条坑。

**三个域名级档位是纯 REJECT，不含 URL 重写和脚本，不需要开启 MITM、不用装证书。**

**三个 URL 级档位都需要 MITM**（`[URL Rewrite]` + `[Script]`），不打算开 HTTPS 解密就别装。
它们不是三选三，而是 **`antidad-rewrite` = `splash` + `zhihu` + B站** —— 装了整合档就不需要另外两个。

> **子集档为什么还留着**：解密面即开销。如果你不刷 B站，就没有理由为它解密 8 个域、
> 更没有理由为它承担 9 条 `requires-body=1` 脚本。子集档是「按需缩小解密面」的出口。

---

## 三、安装

模块地址（**推荐装前两条**；后四条按需）：

```
# ── 推荐组合：域名级 + URL 级 ─────────────────────────────
https://cdn.jsdelivr.net/gh/ace1892/shadowrocket-antidad@main/modules/antidad-full.module
https://cdn.jsdelivr.net/gh/ace1892/shadowrocket-antidad@main/modules/antidad-rewrite.module

# ── 备选：域名级另两档 ───────────────────────────────────
https://cdn.jsdelivr.net/gh/ace1892/shadowrocket-antidad@main/modules/antidad-lite.module
https://cdn.jsdelivr.net/gh/ace1892/shadowrocket-antidad@main/modules/antidad-strict.module

# ── 备选：URL 级子集（已含在 antidad-rewrite 里，不要重复装）──
https://cdn.jsdelivr.net/gh/ace1892/shadowrocket-antidad@main/modules/antidad-splash.module
https://cdn.jsdelivr.net/gh/ace1892/shadowrocket-antidad@main/modules/antidad-zhihu.module
```

**方式一 · 点链接**（iPhone 上直接点上面任意一条，会调起小火箭）

**方式二 · 手动添加**

1. 小火箭 →「配置」→「模块」→ 右上角 `➕` → 粘贴链接 → 下载
2. 回来后点该模块右侧 `···`，确认「启用」已打开

**方式三 · 扫码**（用另一台设备渲染 `install.html` 后用 iPhone 相机扫）

安装后**必须验证**，不要只看开关是绿的：

1. 「配置 → 编辑配置 → 规则 → 规则集上左滑 → 预览」，确认规则真的加载进来了
2. 用「测试规则」输入一个广告域名（例如 `pos.baidu.com`），看命中策略是否为 REJECT

> ⚠️ **生效前提**：「全局路由」必须设为**「配置」**。切到「代理」或「直连」，含 `[Rule]` 的模块不工作。

---

## 四、白名单（误杀放行）

不要改 `modules/*.module` —— 那是生成产物。改 `whitelist.txt`：

```
example.com                  → DOMAIN-SUFFIX,example.com,DIRECT
DOMAIN-KEYWORD,某个关键词    → DOMAIN-KEYWORD,某个关键词,DIRECT
DOMAIN,exact.example.com     → DOMAIN,exact.example.com,DIRECT
```

改完 push（或直接在 GitHub 网页上编辑），`build-modules` 会自动重建模块。

**为什么必须放在最前面**：规则自上而下、命中即停。放行写在 REJECT 之后等于没写。

**当前默认放行了 3 条**，都有明确依据（上游 curators 自己也把它们列入了需要人工判断的清单）：

| 放行项 | 原因 |
|---|---|
| `wxs.qq.com` | 微信小程序资源域。上游按后缀整体拦截，会波及小程序内图片/资源加载 |
| `umeng.com` | 友盟统计。被大量国产 App 用作崩溃上报与推送通道，整体拦截可能影响推送到达 |
| `app-analytics-services.com` | Apple 分析（遥测）。拦掉收益极低，iOS 部分诊断会走它 |

`whitelist.txt` 第二节里另有一批**注释掉的按需放行项**（拼多多接口域、Google 广告域），确认被误杀后再取消注释。

> **白名单只注入「含域名级黑名单」的档位**：`antidad-full` / `antidad-lite` / `antidad-strict`。
> URL 级档位（`antidad-rewrite` / `splash` / `zhihu`）没有任何域名级 `REJECT`，
> 白名单在那里没有放行对象 —— 注进去只会让两个模块出现逐字重复的同样 3 行。
> 这条由 `audit_layers.py` 强制断言。

---

## 五、⚠️ 严格版的额外风险

`antidad-strict.module` 多引用的 LOWERTOP AntiAD，作者自述「**本规则集仅适用于自用需求**」。它除了广告，还拦了大量遥测与推送域。实测会被它拦掉的域名包括：

| 域名 | 影响 |
|---|---|
| `tpns.qq.com` | 腾讯移动推送服务 → **可能造成部分 App 收不到推送** |
| `l.qq.com` | QQ 短链跳转域 |
| `wup.imtt.qq.com` | QQ 浏览器更新服务 |
| `pos.baidu.com` / `eclick.baidu.com` | 百度统计与点击（拦掉是预期行为） |
| `mon.zijieapi.com` / `dm.bytedance.com` / `ugdtimg.com` | 字节系埋点（拦掉是预期行为，但影响面大） |
| `msmp.abchina.com.cn` | 农行 App 的 VPN 检测域 —— 拦掉可避免被判定为代理环境，**但属于对银行 App 的规避行为，自行判断** |

**只在你接受「部分 App 功能可能异常」时再装严格版。**

---

## 六、知乎补丁 `antidad-zhihu.module`（可选，需 MITM）

### 为什么单独做一个

知乎的开屏广告、信息流 banner、相关推荐，走的都是**正经域名下的路径**，例如：

```
https://api.zhihu.com/commercial_api/launch_v2?...      ← 开屏
https://www.zhihu.com/commercial_api/banners_v3/mobile_banner
https://api.zhihu.com/brand/question/123/card?...       ← 品牌卡片
```

HTTPS 把请求切成「域名 + 加密路径」两段，**域名级规则只看得到域名那一段**，所以 `antidad-full.module` 里那 29.6 万条域名规则在原理上就拦不到它们。要拦只能解密后按路径匹配 —— 这就是这一档存在的原因。

顺带说明：自建库的域名集里含 "zhihu" 的只有 4 条，且**全是误匹配**（`.bozhihua.com`、`.sibozhihui-lc.com`、`.zhihu.xmcimg.com`、`.zhihuiduijian.com`），一条都不管用。

### 规则为什么是「内联」而不是远程引用

`sources.json` 里这两条源的 `kind` 都是 `INLINE` —— 规则**原文嵌在模块里**，不写 `RULE-SET,<url>`。

理由就是本文第一节说的那件事：上游 blackmatrix7 会重组目录，本项目已经因为「模块引用上游文件被删」吃过一次亏（第三方知乎模块 404 静默死亡）。这套规则自 2025-06 未变更、总共 1.3 KB，内联进来可彻底消除 404 风险；代价是上游真更新时不会自动跟随，需要手动更新 `sources.json` 里的 `rules` 再重新构建。

**`verify.py` 仍然每天盯着上游那个 `.sgmodule`** —— 条数下降超 15% 或字节缩水超 30% 会开 issue。看到 `zhihu-domain` / `zhihu-url` 报漂移，就是官方改了规则，需要人工同步一次。

### 2026-09-28：按「层」拆成两个源

原来是一条 `zhihu-inline`（13 条混在一起），现在拆开：

| 源 | 条数 | 归到哪个模块 | 为什么 |
|---|---|---|---|
| `zhihu-domain` | 4 | `antidad-full` / `strict` / `zhihu` | `DOMAIN` ×2 + `IP-CIDR` ×2，是**连接层 REJECT**，根本不需要解密 —— 是域名级模块的活 |
| `zhihu-url` | 8 | `antidad-rewrite` / `zhihu` | 7 条 `URL-REGEX` + 1 条 `USER-AGENT`，**必须解密才生效** |

拆的理由有两个，都是「谁该干什么」的问题：

1. 把那 4 条留在 URL 级模块里，等于让一个「纯 URL 层」的模块干连接层的活 ——
   而且**只装 `antidad-rewrite`、不装 `antidad-full` 的人会漏拦这 4 条**。
2. `USER-AGENT` 反过来不能挪去域名级模块：**HTTPS 下 UA 在密文里，不开解密读不到**，
   挪过去就是永远失效。它的归类依据是「需不需要解密」，不是「长得像不像域名规则」。

另外删掉了原第 5 条 `DOMAIN,appcloud2.in.zhihu.com,REJECT` —— 实测该域**已经躺在
blackmatrix7 Advertising 域名集里**（anti-AD 亦有），域名级模块早已整域 REJECT，
留着就是两个模块之间的死代码。

### 解密范围（`[MITM]`）

```
hostname = %APPEND% api.zhihu.com,www.zhihu.com,zhuanlan.zhihu.com,103.41.167.226,103.41.167.234,103.41.167.235,103.41.167.236
```

- `%APPEND%` 表示**追加**，不会覆盖其它模块或配置里已声明的解密域名
- 三个域名对应规则里的 `api.zhihu.com` / `www.zhihu.com` / `zhuanlan.zhihu.com`
- 四个 IP 是官方规则特意列的 —— 知乎有**走 IP 直连的广告接口**，只按域名解密会漏

> 官方配套的 `ZhihuAds_MITM.sgmodule` 只声明了 `api.zhihu.com` 和 `zhuanlan.zhihu.com`，**漏了 `www.zhihu.com`**，而规则里 3 条用到了它。本模块已补上。

### 装它的前提与代价

**13 条规则里，4 条不需要解密就生效、9 条必须解密**（前者已挪进域名级模块）：

| 规则类型 | 条数 | 需要 MITM？ | 在哪 | 拦什么 |
|---|---|---|---|---|
| `DOMAIN` | 2 | ❌ 不需要 | `antidad-full` | `mqtt.zhihu.com`、`sugar.zhihu.com` |
| `IP-CIDR` | 2 | ❌ 不需要 | `antidad-full` | 知乎广告服务器的 IP + IPv6 |
| `URL-REGEX` | 7 | ✅ **需要** | 本模块 | 开屏 `launch_v2`、banner、品牌卡片、相关推荐 |
| `USER-AGENT` | 1 | ✅ **需要** | 本模块 | `AVOS*`（知乎系的旧 UA）|

开屏广告和 banner 都在那 7 条里 —— **不开解密，核心收益拿不到**。

| 项 | 要求 |
|---|---|
| HTTPS 解密 | **必须开**（设置 → HTTPS 解密） |
| 根证书 | **必须已安装并信任**（设置 → 通用 → 关于本机 → 证书信任设置）|
| 全局路由 | 必须是「配置」 |
| 代价 | 4 个 IP + 3 个域名进入解密范围；开了 MITM 后其它模块的 `URL-REGEX` 规则也随之生效 |
| 收益 | **只有知乎一家**。其他 App 内广告要另装对应模块 |

如果只想解决知乎而且不想扩大解密面：本模块的 `[MITM]` 只声明这 7 个目标，是能达到的最小范围。

---

## 七、URL 级整合档 `antidad-rewrite.module`（主力，需 MITM）

### 里面装了什么

一个模块收齐所有 URL 级去广告，**规则全部内联**（不远程引用规则集），**脚本也全部自持**（收在 `js/`，不指向别人的仓库）。
**本模块不含任何域名级规则，也不含白名单** —— 那是 `antidad-full` 的活（见第七节末与第十节第 23 条）：

| 来源 | 条数 | 目标段 | 覆盖内容 |
|---|---|---|---|
| App 开屏 | 9 | `[URL Rewrite]` | 闲鱼 / 高德地图 / 百度地图 / 京东 / 美团 / 拼多多 / 小红书 的开屏接口 |
| B站 URL 重写 | 10 | `[URL Rewrite]` | 开屏 / 搜索默认词 / 首页活动 / 会员购物料 / 播放页小卡片 / 相关推荐 / 大家都在搜 / 动态话题 / 漫画页 |
| 知乎 URL 层 | 8 | `[Rule]` | 7 条 `URL-REGEX` + 1 条 `USER-AGENT`（来自 blackmatrix7 官方 ZhihuAds） |
| B站 脚本 | 9 | `[Script]` | 观影页 / 开屏预加载 / 热搜发现 / 推荐流 / 追番 / 直播 / 动态 / Proto / 动态广告 |
| 微信公众号 脚本 | 1 | `[Script]` | 文章底部广告（`mp/getappmsgad`） |

`[Rule]` 段只有 8 行 —— 全是**必须解密才生效**的规则（`URL-REGEX` 与 `USER-AGENT`）。
域名层的那 4 条（`mqtt` / `sugar` 域名 + 2 个腾讯云 IP）已移到 `antidad-full`。

**为什么要合并**：装三个模块时，解密面是三者之和，而且**你看不见它**。
合成一个模块后，`[MITM]` 是一份可审计的名单，`check_mitm.py` 也能一次校验到位。

### 解密目标 25 个

```
App开屏(9)   acs.m.taobao.com  m*.amap.com  newclient.map.baidu.com
             api.m.jd.com  bdsp-x.jd.com  wmapi.meituan.com
             api.pinduoduo.com  api.yangkeduo.com  www.xiaohongshu.com

B站(8)       app.bilibili.com  api.bilibili.com  api.biliapi.net  api.biliapi.com
             api.bilibili.net  api.vc.bilibili.com  api.live.bilibili.com
             manga.bilibili.com          - 排除：-*cdn*.biliapi.net  -*tracker*.biliapi.net

知乎(7)      api.zhihu.com  www.zhihu.com  zhuanlan.zhihu.com
             103.41.167.226 / .234 / .235 / .236

微信(1)      mp.weixin.qq.com
```

**全是 API / 接口域，没有一个图片或视频 CDN。** 这是相对 NoAd（153 个，含 6 个高流量 CDN 通配符）的关键差别。

> ⚠️ **`%APPEND%` 是整域解密，不认路径**。`acs.m.taobao.com` 一旦声明，该域**所有**请求都过解密，
> 无法只针对闲鱼那一条 `/gw/mtop.taobao.idle.*`。这是 `[URL Rewrite]` 机制的固有粒度限制。

### 为什么做这个（而不是继续用 NoAd）

第三方通用模块能拦 App 内广告，但**代价是解密面极宽**。以
`deezertidal/shadowrocket-rules` 的 `AdBlock.module`（NoAd）为例，实测：

| 项 | 数值 |
|---|---|
| `[URL Rewrite]` 规则 | 264 条 |
| 规则涉及的域名 | 206 个 |
| `[MITM]` 解密目标 | **153 个** |
| 其中高流量图片/视频 CDN 通配符 | ≥6 个：`img*.360buyimg.com`、`p*.meituan.net`、`*.tv.sohu.com`、`pic?.ajkimg.com`、`img*.10101111cdn.com`、`*.k.sohu.com` |

**先纠正一个常见误解**：MITM 只对**实际访问**的域做解密 —— 声明 153 个 ≠ 开了 153 个的开销。
所以"砍掉用不到的域"省不了电；真正省钱的是**砍掉你会频繁访问的高流量域**。

而这些 CDN 域一旦被访问，**整域流量都要过一遍 TLS 解密再加密**：刷一次电商，
一屏商品图就是 MB 级流量，而广告 API 只有几十 KB。**图片流量占 90% 以上 ——
这才是「只开一个通用模块就明显发热」的物理原因。**

| 项 | NoAd | 本模块 |
|---|---|---|
| 解密目标 | 153 | **25** |
| 其中高流量 CDN | 6+ 个通配符 | **0** |
| 开屏广告 | 拦 | 拦（7 个 App） |
| 知乎 / B站 / 公众号 | 部分 | 拦 |
| 商品列表里的图片广告位 | 拦 | 不拦（这是省电的代价） |

### 覆盖范围

规则见上表；开屏那 9 条的明细：

| App | 目标 |
|---|---|
| 闲鱼 | `acs.m.taobao.com` → `mtop.taobao.idle.home.welcome` |
| 高德地图 | `m\d.amap.com` → `valueadded/alimama/splash_screen` |
| 百度地图 | `newclient.map.baidu.com` → `phpui2/?qt=ads` |
| 京东 | `api.m.jd.com`（`functionId=start` / `queryMaterialAdverts`）+ `bdsp-x.jd.com/adx/` |
| 美团 | `wmapi.meituan.com/api/v\d/startpicture` |
| 拼多多 | `api.(pinduoduo\|yangkeduo).com/api/cappuccino/splash` |
| 小红书 | `www.xiaohongshu.com/api/sns/v\d/system_service/splash_config` |

> **淘宝不在覆盖范围内**：NoAd 原档里 `acs.m.taobao.com` 那 3 条分别是**闲鱼**（`mtop.taobao.idle.*`）、
> **飞猪**（`mtop.trip.*`）、**淘票票**（`mtop.film.*`），都不是淘宝 App 本身 —— 淘宝没有可用的开屏接口规则。

### 规则为什么内联

这些接口路径由 App 自己的代码决定，**多年不变**。内联之后与上游彻底脱钩，
上游怎么改都影响不到本模块。真有一天某条广告回来了，说明那条接口变了，改一行重新构建即可。

**换句话说：不需要跟着上游更新。**

**`[Script]` 也一样自持**：脚本 JS 有 27~107 KB，没法内联进模块，所以 `script-path` 本来只能指向别人的仓库 ——
上游删文件就静默失效。现在三个 B站脚本都收进了 `js/`，`script-path` 指自家 jsDelivr，这条风险已消除。
详见下方 [`js/` 一节](#js--为什么不直接引用别人的脚本)。

### 被剔除的东西（有意为之）

B站上游 `biliad.module` 里还有这些，**本模块不收**，因为它们不是去广告：

| 剔除项 | 为什么 |
|---|---|
| 1080P 高码率 + 4K 画质解锁 | 画质增强 |
| 去除统一设置皮肤 / 标签页处理 / 我的页面处理 | 界面定制 |
| 繁体 CC 字幕转简体 | 字幕转换 |
| 屏蔽 IP 请求 | 隐私，不是广告 |
| 解除 SIM 卡地区限制（302 重写） | 地区解锁；且目标域 `app.biliintl.com` 不在解密名单里，本来就是死规则 |

要哪条加回来说一声，改 `sources.json` 重建即可。

### 子集档：`antidad-splash` / `antidad-zhihu`

两者都是本模块的**真子集**（分别只含开屏 9 条 / 知乎 13 条），**不要与本模块同时装**。

留着它们的理由：**解密面即开销**。不刷 B站，就没必要为它解密 8 个域、
更没必要承担 9 条 `requires-body=1` 脚本。子集档是「按需缩小解密面」的出口。

顺带一提，`biliad.module` 用的是同一种思路：它的 `[MITM]` 里有
`-*cdn*.biliapi.net`、`-*tracker*.biliapi.net`（**前缀 `-` 表示排除**），主动不解密视频 CDN。
**审计第三方模块时，看它有没有 `-` 排除项，就能判断作者是「粗放」还是「精细」。**

---

## 八、仓库结构与自动化

```
.
├── modules/                     # 生成产物，不要手改
│   ├── antidad-full.module
│   ├── antidad-lite.module
│   ├── antidad-strict.module
│   ├── antidad-rewrite.module   # ★ [URL Rewrite] + [Script]，需开 HTTPS 解密
│   ├── antidad-zhihu.module     # 重写整合的子集
│   └── antidad-splash.module    # 重写整合的子集
├── dist/                        # 生成产物，不要手改
│   └── divert.conf              # ★ 自建【分流】订阅，和反广告无关，见第十二节
├── whitelist.txt                # ← 改这个
├── sources.json                 # ← 上游登记表 + 实测基线，改这个（section 字段决定规则落到哪个段）
├── js/                          # 自持的第三方脚本（vendored），见下方说明。⚠️ 不要删
│   ├── bilibili_json.js         #  33 KB  B站（7 条规则）| 上游已消失，靠镜像找回
│   ├── bilibili-proto.js        # 107 KB  B站 Proto（1 条）| app2smile/rules
│   └── bilibili_dynamic.js      #  45 KB  B站动态（1 条）| yjqiang/surge_scripts
├── scripts/
│   ├── build.py                 # 由 whitelist + sources 生成 modules；带 inline_filtered 的源在构建时拉上游、剔除指定类型后内联
│   ├── verify.py                # 校验上游可达性、内容漂移、以及 script-path / 自持副本是否还活着
│   ├── check_mitm.py            # 校验每条 URL 级规则（含 [Script] 的 pattern）都被 [MITM] 覆盖
│   ├── audit_layers.py          # ★ 层级断言：域名级只管域名、URL 级只管 URL、白名单不重复
│   └── build_divert.py          # ★ 生成 dist/divert.conf（分流订阅）；6 组断言见第十二节
├── STATUS.md                    # 自动生成的校验状态，不要手改
└── .github/workflows/
    ├── build.yml                # 改 whitelist/sources/scripts 时重建 + 校验；另有每日定时（内联源要跟上游）
    ├── divert.yml               # 每日重建 dist/divert.conf（独立 workflow，见第十二节）
    └── verify.yml               # 每天 09:00(UTC+8) 校验上游，异常开 issue
```

### `audit_layers.py` —— 把「分层」变成会失败的断言

2026-09-28 做了一次人工审计，结论是**两个模块互相越界**：URL 级模块里躺着 4 条域名级规则
和一条重复的白名单；域名级模块里则通过上游规则集带进了 14 条 `URL-REGEX`。
手工查一次不够 —— 得让它在每次构建时自动失败。三条断言：

| 断言 | 抓什么 |
|---|---|
| 一个模块不得同时含域名层与 URL 层规则 | 「零解密的模块」里塞了只有解密才生效的规则，或「URL 级模块」在做连接层拦截 |
| 白名单只允许出现在含域名级黑名单的档里 | 两个模块出现**逐字重复的 3 行白名单**（原来就有） |
| 子集档的每条规则都必须在父档里存在 | `splash` / `zhihu` 悄悄跑偏、和父档不一致 |

域名层 = `DOMAIN` / `DOMAIN-SUFFIX` / `DOMAIN-KEYWORD` / `IP-CIDR` / `RULE-SET` / `DOMAIN-SET`；
URL 层 = `URL-REGEX` 行、`[URL Rewrite]` 段、`[Script]` 段、`[MITM]` 段。
两边的分界不看规则「长得像什么」，看**需不需要 HTTPS 解密** ——
这就是为什么 `USER-AGENT`（HTTPS 下 UA 在密文里）算 URL 层，而 `IP-CIDR` 算域名层。

### `js/` —— 为什么不直接引用别人的脚本

`[Script]` 规则里的 `script-path` 只能指向一个 URL，**脚本没法内联进模块**。所以每个脚本都是一个外部依赖：

> 上游删掉文件 → 模块还在、解密照做、**脚本不跑** → 广告悄悄回来，你不会收到任何报错。

这件事在 2026-09-24 真实发生过：`biliad.module` 引用的
`deezertidal/private/js-backup/Script/bilibili_json.js` 被上游连目录一起清空，
而且**仓库历史被重写过** —— 73 个 fork 和提交历史里都找不回该文件，
7 条 B站脚本规则全部静默失效，`verify-sources` 连续 4 天失败。

**三个脚本全部已自持**，`script-path` 一律指自家 jsDelivr：

| 文件 | 上游 | 最后改动 | 说明 |
|---|---|---|---|
| `js/bilibili_json.js` | `deezertidal/private` | 2022-11-08 | 上游已整目录清空 + 重写历史，靠 GitHub 代码搜索从镜像找回（5 个内容一致的副本）|
| `js/bilibili-proto.js` | `app2smile/rules`（MIT）| 2024-11-02 | 文件近 2 年未变，仓库仍活跃 |
| `js/bilibili_dynamic.js` | `yjqiang/surge_scripts`（未声明许可证）| 2023-10-02 | ⚠️ 上游近 3 年未更新，B站改接口时它会先失效 |

**收进来的脚本不需要跟随上游更新** —— 除非 B 站改了对应接口，否则无需改动。
来源、作者、commit、镜像 sha256 都写在文件头的注释块里，`sources.json` 的 `vendored`
字段另外登记了 `file_bytes` / `file_sha256_16`，由 `verify.py` 的 `check_vendored()` 校验。

⚠️ **`js/` 里的文件不要删、不要改**。自持副本是「静默死亡」的终极解法，但它一旦被误删，
规则会以完全相同的方式失效 —— 而且**不会再有任何上游信号可依赖**。所以校验逻辑盯的是自己。

安全体检（2026-09-28，三个脚本逐项过）：无 `eval` / `new Function` / 远程代码加载；
不读取任何凭据（无 keychain / cookie / token 访问）；无对外网络请求。
`bilibili-proto.js` 里唯一一处 `require()` 位于 text-decoder polyfill 内、被
`typeof module && module.exports` 守卫 —— 小火箭运行时没有 `module` 对象，该分支不会执行。

剩下的远程依赖只有规则集（anti-AD / blackmatrix7 的 `DOMAIN-SET`、`RULE-SET`）和
微信公众号那一条脚本（`NobyDa/Script` 的 `Wechat.js`），`verify.py` 每天盯活。

本地运行（只用标准库，不需要装依赖）：

```bash
python3 scripts/build.py                  # 重建 modules/（带 inline_filtered 的源需要联网）
python3 scripts/build.py --check          # 只校验是否需要重建
python3 scripts/verify.py                 # 校验上游
python3 scripts/verify.py --update-baseline   # 把当前实测写回 sources.json
python3 scripts/check_mitm.py             # 校验 MITM 覆盖（缺声明=规则静默失效）
python3 scripts/audit_layers.py           # 校验分层（域名级只管域名、URL 级只管 URL）
```

**两点和以前不一样**：

1. `build.py` 现在会**联网** —— 它要为 `inline_filtered` 的源（`bm-keyword-ip` / `bm-lite`）
   拉上游并剔除 `URL-REGEX`。拉不到会直接报错退出，**不静默退回旧内容**
   （否则你会以为模块更新了，其实还是几天前的快照）。
2. `build.yml` 因此多了**每日定时**（04:30 UTC+8）—— 那两个上游文件每 1~2 天更新一次，
   没有定时就吃不到。域名主体不受影响，它走 `DOMAIN-SET` 远程引用，始终跟随上游。

**漂移检测怎么判**：规则集每天更新，内容哈希必然变，所以不用哈希当判据。`verify.py` 用「条数」和「字节数」双指标 —— 条数下降超过 15%、或字节缩水超过 30%，就判定异常并开 issue。这能抓到上游被清空、换格式、或不可达。

---

## 九、设计取舍

**Q：为什么不把规则集直接存进仓库，彻底不依赖上游？**

A：代价大于收益。存进来约 7.7 MB（双源并集），Git 会随每日更新膨胀；而且上游本来就在每天更新，自己搬运反而更容易变旧。**当前方案唯一的依赖是上游规则集的 URL 不变**，而 blackmatrix7（8 年、规则集被大量配置引用）和 anti-AD 都极其稳定。`verify.py` 每天盯着，真出问题会开 issue。

如果以后确实需要完全自主，可以加一条 workflow 把上游合并后推到 `dist` 分支，把模块指向自己的 `dist` —— 现有的 `build.py` 数据结构已经为此留好了位置。

**Q：为什么只做了知乎的 URL 重写，不做开屏广告 / 其他 App？**

A：刻意克制。那类规则要覆盖 100+ App，通常意味着 MITM 名单扩大到 150～240 个域名、外加十几条第三方 JavaScript 脚本 —— 而**模块里的脚本能看到被解密的流量**。收益与风险不成比例。

知乎这一档是个例外，理由充分：官方 `ZhihuAds` 是**纯规则、零脚本**（13 条，其中 7 条 URL 正则），解密范围只有 7 个目标，是「最小可行 MITM」。其他 App 请单独装经过审查的现成模块，并按需逐个评估。

**Q：为什么用 jsDelivr 而不是 raw.githubusercontent.com？**

A：实测 `raw.githubusercontent.com` 在本机**间歇性不通**（同一次测试中一条 200、一条 000），`cdn.jsdelivr.net` 全部 200 含大文件。代价是 jsDelivr 的 `@分支` 引用有最长约 12 小时缓存 —— 规则集不需要实时，可接受；但**不要**用它测「刚改完的东西生效了没」。

---

## 十、已知坑

1. **域名集必须用 `DOMAIN-SET` 引用**，关键词/IP 集必须用 `RULE-SET`。用错等于没拦。
2. **`AdvertisingLite` 是 `Advertising` 的兄弟目录，不是子目录**。拼成 `.../Advertising/AdvertisingLite/...` 会 404。本仓库的 `sources.json` 里已按正确路径登记。
3. **白名单必须在 REJECT 之前**，否则不生效。
4. **全局路由必须是「配置」模式**。
5. **不要一次性装完所有反广告模块**。模块间规则会叠加，出问题难定位。一个档位一个档位来。
6. 家里如果有 AdGuard Home 之类的 DNS 层拦截，**家庭 Wi-Fi 下已经覆盖大部分广告域名**。本模块的真正价值在**蜂窝数据和外部 Wi-Fi** 场景。
7. **上游规则集是「混合类型」的，引用它等于把 URL 层规则塞进域名级模块**。`blackmatrix7 Advertising.list` 781 行 = 278 `DOMAIN-KEYWORD` + 489 `IP-CIDR` + **14 `URL-REGEX`**，上游自己的 DESCRIPTION 就写着「分流规则中含有 URL-REGEX 类型，建议搭配 MITM 使用」。这 14 条在本项目里**全是死代码**：10 条的落点域早就躺在域名集里被整域 REJECT，剩下 4 条（`ad\d.sina.com`、`app.58.com/api/log/`、`cdn-1rtb.caiyunapp.com/creative/`、`/\d+/sign_d`）因为本模块从不解密那些 host 而永不生效。但「不生效」是靠**外部条件**维持的 —— 谁装一次 bm7 的 `Advertising_MITM.conf`（200+ host）它们就活了。已于 2026-09-28 在**构建时剔除**（`inline_filtered`），见第 23 条。
8. **上游删路径 → 模块 404 静默死亡**。第三方模块如果引用了 `raw.githubusercontent.com` 或 jsDelivr 的具体文件路径，上游一旦搬目录，模块不会报错，只是**一条规则都不生效**，而 MITM 解密照旧消耗电量。判断方法：把模块里引用的每个 URL 单独 curl 一次看是不是 404。本仓库因此把知乎那 13 条**内联**进模块（拆成 `zhihu-domain` 4 条 + `zhihu-url` 8 条）。
9. **开了 MITM 就必须同时开「HTTPS 解密」并信任根证书**，缺一不可（iOS 还要在「关于本机 → 证书信任设置」手动打开）。三项里缺任何一项，`URL-REGEX` 规则都静默失效。
10. **不要把证书固定的域名放进 `[MITM]`**（银行、支付、证券类）。解密失败会让那些 App **直接连不上网**，比不拦广告糟得多。
11. **`^https?://...` 形态的规则属于 `[URL Rewrite]` 段**，写进 `[Rule]` 段是非法语法（小火箭不会报错，只是不生效）。本仓库用 `sources.json` 的 `section` 字段区分，渲染时自动落到正确的段。
12. **`[MITM]` 漏声明 = 规则静默失效**。规则里出现 `\d`、`\w`、`(a|b)` 交替写法时，肉眼核对极易漏（例如 `m\d\.amap\.com` 必须在 `[MITM]` 写 `m*.amap.com`，`api.(bilibili|biliapi).(com|net)` 必须展开成 4 条）。用 `scripts/check_mitm.py` 自查，已接入 CI。
13. **判断第三方模块"粗放"还是"精细"，看它的 `[MITM]` 有没有 `-` 排除项**。`-` 前缀表示排除，精细的模块会主动排除高流量 CDN（如 `biliad` 的 `-*cdn*.biliapi.net`）。**没有任何 `-` 排除项的通用模块，会把图片/视频 CDN 一并解密 —— 这是"一开就发热"的主因**，不是规则条数。
14. **MITM 只对"实际访问的域"解密**。声明了 153 个域不等于产生 153 份开销；砍掉你根本不会访问的域省不了电。省电只能靠**砍掉你频繁访问的高流量域**。
15. **规则写错段 = 静默失效**。三种段的语法互不通用：`[Rule]` 收 `DOMAIN,` / `URL-REGEX,` / `RULE-SET,`…；`[URL Rewrite]` 收 `^正则 target`；`[Script]` 收 `名字=type=...,pattern=...,script-path=...`。把 URL 重写规则塞进 `[Rule]`，小火箭**不报错，只是整批忽略**。本仓库用 `sources.json` 的 `section` 字段路由，`build.py` 分段渲染。
16. **`[Script]` 的 `pattern=` 也要 `[MITM]` 覆盖**，漏了同样静默失效 —— 而且更隐蔽：脚本不跑，你不会看到任何报错，只会觉得"广告怎么又回来了"。`check_mitm.py` 已把 `[Script]` 段纳入检查。
17. **正则里的 `(a|b)` 交替在 `[MITM]` 里要展开**。上游 `biliad` 的规则写 `api.(bilibili|biliapi).(com|net)`，展开是 **4 个组合**，但它的 `[MITM]` **只声明了 2 个** —— 另 2 条分支静默失效。本仓库补齐为 4 个（声明天生不会被访问的域，成本为零）。
18. **`[MITM]` 里的 `-` 排除项要排在末尾**。hostname 是「先声明、后排除」，顺序反了排除可能不生效。`build.py` 的 `collect_mitm()` 会自动把 `-` 项统一挪到最后。
19. **`script-path` 是最脆弱的一环 —— 上游删文件是「静默死亡」**。规则在、模块在、解密照做，只有脚本不跑了，你不会看到任何报错。更麻烦的是：**上游可能连 git 历史一起重写**，这时 fork 和提交历史都取不回文件（2026-09-24 实测，73 个 fork 全查过，无一留存）。补救按这个顺序：
   1. `GET /repos/<o>/<r>/commits?path=<路径>` —— 有历史就能用 `raw/<sha>/<路径>` 取回
   2. 遍历 fork（`/repos/<o>/<r>/forks?per_page=100`）逐个试 raw —— fork 停在删除之前的话还在
   3. **GitHub 代码搜索按文件名找镜像**：`filename:bilibili_json.js`。同名镜像往往有几十个，比内容 sha256 取**多数派**（本次 56 个结果里 5 个完全一致）
   4. 长期方案：**收进本仓库**（`js/`），不再依赖别人 —— 本项目三个脚本**已全部落地**，见 [`js/` 一节](#js--为什么不直接引用别人的脚本)
20. **校验脚本的退出码会连带打断「告警步骤」**。`verify.yml` 里这一步踩了坑：
   ```yaml
   - name: 写 STATUS.md
     run: |
       {
         echo '```'
         python3 scripts/verify.py     # ← 发现异常时返回 1
         echo '```'
       } > STATUS.md                   # ← 整个块的退出码 = 最后一条命令的退出码 → 本步 FAIL
   ```
   结果：`写 STATUS.md` 打挂 → 后面「提交 STATUS.md」「异常时开 issue」**全部被跳过** → 4 天里一个 issue 都没建出来。正确写法是 `python3 scripts/verify.py || true`，异常与否交给 `continue-on-error` 的 `outcome` 判定，并在**最后**单独加一步 `exit 1` 来触发失败通知。
21. **同一个请求可以命中两条 `[Script]` 规则，而且谁都没报错**。上游 `biliad.module` 里：
   - `bili_8` pattern = `bilibili.app.(view.v1.View/View|dynamic.v2.Dynamic/DynAll)$`
   - `bili_9` pattern = `bilibili.app.dynamic.v2.Dynamic/DynAll$`

   `DynAll` 那个接口**同时落在这两条的范围内** —— 一个请求要跑两个 100 KB 级的 protobuf 脚本，谁后 `$done` 谁生效。这是上游原始写法，本仓库**保持原样未改动**（改了等于替上游做产品决策）。真要腾开销，删掉 `sources.json` 里 `bili_9` 那一条是最省事的落点。排查同类问题时记住：**规则重叠不会报错，只会静默多解密、多跑脚本**。
22. **别把两个有交集的源「相加」当并集**。本项目在 §二 写过「anti-AD 与 blackmatrix7 交集只有 1,926 条、去重后 382,242 条」——这是 2026-09-21 的错误算法留下的，382,242 其实就是 `102,114 + 285,470` 的近似和，**两源根本没做去重**，交集的 1,926 也是这个错误前提推出来的。2026-09-28 按域名归一化（统一 `lstrip('.')`）复测：**交集 91,590 条、并集 295,994 条**，差 47 倍。
    两个坑叠在一起：① 没去重；② 两个列表的**前导点格式不一致**（anti-AD 全部带 `.`，blackmatrix7 域名集是带点/不带点混排，实测 269,029 : 16,441），直接按行文本比对会漏掉一半匹配。**凡是「A 与 B 互补」这类结论，必须先把两边归一化再算交集。**
23. **⭐ 「域名级」和「URL 级」不是命名习惯，是硬约束 —— 而且会互相制造死代码**。2026-09-28 的审计实测出的两类越界：

    | 越界 | 具体 | 后果 |
    |---|---|---|
    | URL 级模块里塞了域名级规则 | `antidad-rewrite` 的 `[Rule]` 里有 3 条 `DOMAIN` + 2 条 `IP-CIDR` + 一份 3 行白名单 | 该模块是「纯 URL 层」却干连接层的活；**只装它不装 `antidad-full` 的人会漏拦这 4 条**；白名单在它这儿没有任何放行对象，纯粹制造两模块逐字重复 |
    | 域名级模块里塞了 URL 级规则 | `antidad-full` 通过 `Advertising.list` 带进 14 条 `URL-REGEX` | 上面第 7 条 |
    | 跨模块死代码 | `antidad-rewrite` 里 `DOMAIN,appcloud2.in.zhihu.com,REJECT` | 该域已在域名集里被整域 REJECT，URL 规则**拿不到这条请求** |

    **判断一个规则属于哪层，只看「需不需要 HTTPS 解密」，不看它长得像不像域名规则**：

    | 规则 | 需要解密？ | 归哪层 | 反直觉之处 |
    |---|---|---|---|
    | `DOMAIN` / `DOMAIN-SUFFIX` / `IP-CIDR` | ❌ | 域名层 | — |
    | `USER-AGENT` | ✅ | **URL 层** | HTTPS 下 UA 在**密文里**，不开解密读不到 —— 挪去域名级模块会永远失效 |
    | `URL-REGEX` | ✅ | URL 层 | 即使它匹配的是某个域，也拿不到解密后的路径 |

    这类问题**不会报任何错**：模块照装、解密照做、广告照旧。所以本项目把结论固化成
    `scripts/audit_layers.py`，构建时强制断言（见第八节），而不是靠人记住。
24. **「剥离上游自带的 URL 规则」只能在构建时做**。`Advertising.list` 每 1~2 天更新一次，既没有「只有关键词/IP 的子文件」可换，也不能把这 14 条搬进 URL 级模块去干活（本模块从不解密那些 host，搬过去还是死代码）。唯一干净的做法是构建时拉取 → 剔除 → 内联。代价是这部分从「运行时永远最新」变成「构建快照」，所以要给 `build.yml` 配上**每日定时**；域名主体照旧走 `DOMAIN-SET` 远程引用，不受影响。反面做法是「保留引用 + 靠注释说明它们不生效」—— 那是**靠外部条件维持的正确性**，别人装一个 bm7 的 MITM 声明就破了。
25. **⭐ jsDelivr 的 `@main` 分支别名有 CDN 缓存，且不会随新提交自动失效** —— 这是「改了没用」的最隐蔽来源。2026-09-29 实锤：

    | 项 | sha256 | 大小 | 对应提交 |
    |---|---|---|---|
    | 线上 `@main`（purge 前） | `1782ffeb…` | 30,135 B | `01238cb`（旧，4 个 DNS 上游） |
    | 线上 `@253374a`（固定 sha） | `9d90b6f6…` | 31,459 B | `253374a`（新，2 个上游 + `#no-h3`） |
    | 本地 `dist/divert.conf` | `9d90b6f6…` | 31,459 B | `253374a` |

    也就是说 `253374a` 已推送成功、`@main` 仍返回上一版。手机端「更新订阅」拿到的就是旧内容，**配置本身没错、用户操作也没错**，纯粹是 CDN 分发滞后。

    **判定方法**：别只 `curl` 比对，要拿 `@main` 与 `@<sha>` **分别抓一次比 sha256**。只测其中一条会得出相反结论。

    **治疗**：`curl https://purge.jsdelivr.net/gh/<owner>/<repo>@main/<path>` 拿 `"status": "finished"` 即算刷新成功（purge 后实测立即生效）。`divert.yml` / `build.yml` 已各加一步，排在 `git push` **之后**执行。`@<sha>` 形态不受缓存影响，可作应急。
26. **光看日志不能判断「配置有没有真的换掉」，要看 DNS 上游指纹**。`dns-server` 是在配置里改的，日志里不会复述这行配置本身，但每一轮 DNS 查询都会把**实际用的上游**打出来。2026-09-29 就是靠这个抓到的：日志里出现 4 个上游（`doh.pub` / `dns.alidns.com` / `223.5.5.5` / `119.29.29.29`）并行发送，而最新配置只写了 2 个 —— 说明手机上跑的仍是旧版。同类指纹还有：`dns over quic … #h3` 是否出现（出现 = `#no-h3` 没生效）、`route manager skip load rule file`（出现 = 本次没有重新编译配置）。

---

## 十一、上游来源与实测基线

基线日期 **2026-09-21**：

| 源 | 引用类型 | 条数 | 大小 | 主页 |
|---|---|---|---|---|
| anti-AD 主列表 | DOMAIN-SET | 100,732 | 2.0 MB | [privacy-protection-tools/anti-AD](https://github.com/privacy-protection-tools/anti-AD) |
| blackmatrix7 Advertising（域名集） | DOMAIN-SET | 283,435 | 5.7 MB | [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script) |
| blackmatrix7 Advertising（关键词+IP+正则） | RULE-SET → **构建时剔除 URL-REGEX 后内联 767 条** | 781 | 26 KB | 同上 |
| blackmatrix7 AdvertisingLite（域名集） | DOMAIN-SET | 37,692 | 596 KB | 同上 |
| blackmatrix7 AdvertisingLite（关键词+IP） | RULE-SET → **构建时剔除 URL-REGEX 后内联 374 条** | 376 | 12.9 KB | 同上 |
| LOWERTOP AntiAD（仅严格档） | RULE-SET | 205 | 8.3 KB | [LOWERTOP/Shadowrocket-First](https://github.com/LOWERTOP/Shadowrocket-First) |
| 知乎 域名/IP 层（整合版 / 严格版 / 知乎补丁） | **INLINE** | 4 | 260 B | blackmatrix7 `rewrite/.../ZhihuAssistantPlus/zhihu_plus.sgmodule` |
| 知乎 URL 层（重写整合 / 知乎补丁） | **INLINE** | 8 | 1.0 KB | 同上 |
| App 开屏广告（仅开屏补丁） | **INLINE** | 9 | 803 B | [deezertidal/shadowrocket-rules](https://github.com/deezertidal/shadowrocket-rules) `AdBlock.module` |

⚠️ 表中 `DIRECT` 类基线是 2026-09-21 的快照，`verify.py` 每天用当前实测对照它做漂移判断；
`measured` 字段里的数字**是漂移基线而不是当前值**，当前值见 `STATUS.md`。

规则内容归各上游作者所有，本仓库只做编排、白名单和校验。

> ⚠️ 关于知乎那套规则的现状：blackmatrix7 官方**现存**的知乎模块是
> `rewrite/Shadowrocket/ZhihuAssistant/ZhihuAssistantPlus/zhihu_plus.sgmodule`（即本仓库内联的来源）。
> 而社区里流传的 `script/zhihu/zhihu_plus.js` 路径**已被作者删除**（现为 404），
> `deezertidal/shadowrocket-rules` 的知乎模块至今仍引用那条死链 —— 装它等于纯耗电、
> 零收益，且小火箭不会报错。本仓库内联规则即是为了让这件事不可能再发生在本项目上。

---

## 十二、另附：自建分流订阅 `dist/divert.conf`

> ⚠️ **这一节和反广告没有关系**，讲的是「代理分流」。放在同一个仓库只是图省事。

### 为什么会有这个文件

上游 `Johnshall/Shadowrocket-ADBlock-Rules-Forever` 的 `lazy_group.conf` 里有 **4 条写错客户端方言的 `RULE-SET`**：

```
line 321  rule/QuantumultX/Apple/Apple.list    → 苹果服务
line 326  rule/QuantumultX/WeChat/WeChat.list  → DIRECT
line 334  rule/QuantumultX/Global/Global.list  → PROXY
line 335  rule/QuantumultX/China/China.list    → DIRECT
```

那 4 个文件里写的是 Quantumult X 方言（`HOST-SUFFIX` / `HOST-KEYWORD` / `HOST-WILDCARD` / `IP6-CIDR`），
**小火箭不识别** → 规则一条都不生效，而且**不报错、无任何可见症状**。

判断是「漏改」而不是「设计」的三条指纹：

1. 同一个文件里 **35 条 `rule/Shadowrocket/...` 对 4 条 `rule/QuantumultX/...`** —— 比例悬殊；
2. 该文件**自己的注释**（第 234/235 行）示范的路径就是 `rule/Shadowrocket/...` —— 自相矛盾；
3. 上游 issue `Johnshall/…-Forever#206`「为什么个别分流规则是QuantumultX？」—— 维护者回「的确是这样的」。

订阅是远程的、改不了源文件（每次更新都会覆盖回来），所以派生一份自己的。

后来这份自建订阅又顺手承担了第二件事：**`[General]` 的 DNS 调优** —— 见下方「改了两处」的第二点。

### 地址

```
https://cdn.jsdelivr.net/gh/ace1892/shadowrocket-antidad@main/dist/divert.conf
```

小火箭 →「配置」→ `➕` → 粘贴 → 下载 → 首页「全局路由」设为「配置」。
**换过来之后要把原来那份 `lazy_group.conf` 停用**，否则两份配置会打架。

### 改了两处

**一、4 条写错客户端方言的 `RULE-SET`**

| 上游那条 | 改成 | 生效条数 | 效果 |
|---|---|---|---|
| Apple → 苹果服务 | `Shadowrocket/Apple/Apple.list` + `Apple_Domain.list` | 1,603 | **主要收益**。`苹果服务` 分组默认出口是 `DIRECT`，原先这批流量落到 `GEOIP,CN`（只接得住中国区 CDN）再落到 `FINAL,PROXY` → 现在 App Store / iCloud / APNs 推送回直连 |
| WeChat → DIRECT | `Shadowrocket/WeChat/WeChat.list` | 33 | 微信规则生效。该文件**已含全部域名**，无 `_Domain.list`，一条就够 |
| China → DIRECT | `Shadowrocket/China/China.list` + `China_Domain.list` | 3,752 | 补回 `GEOIP,CN` 覆盖不到的部分（该组 63 条是 `USER-AGENT`/`IP-CIDR`，GEOIP 按 IP 推断，接不住按 App 分的规则） |
| Global → PROXY | **删除** | — | 与文件末尾 `FINAL,PROXY` 近似等价。补回去只多下 ~556 KB（`Global.list` 6.2 KB + `Global_Domain.list` 550 KB）、多解析 35,104 条。**收益仅剩「境外域名解析到 CN IP 时不再被 GEOIP 误判直连」这一个边缘情形**，代价不成比例 |

⚠️ **最容易踩的下一步坑**：小火箭版规则集是**拆开**的 —— `*.list` 只剩非域名部分
（`USER-AGENT` / `IP-CIDR` / `DOMAIN-KEYWORD`），域名全在 `*_Domain.list`，
**必须 `RULE-SET` + `DOMAIN-SET` 两条一起用**。只把路径从 QuantumultX 换成 Shadowrocket
会丢掉几千条域名，而且同样不报错。脚本会探测并自动补上。

**关于「小火箭版比 QX 版少 278 条」**：逐条核对过，不是能力缺失 ——

- QX 版 272 条 `HOST`（精确匹配）里，**263 条已被同表 `HOST-SUFFIX` 语义覆盖**（`apps.apple.com` 之于 `.apple.com`），属重复写法；
- 真正独有的 **9 条**，且全是 Adobe / 测量类监控域名（`*.omtrdc.net`、`akamaized.net`、`edgekey.net`）；
- 15 条 `HOST-WILDCARD`（如 `apple.*`、`imac.*`）小火箭版无对应写法，上游直接丢弃，大多也被后缀规则覆盖。

**二、`[General]` 里的 `dns-server`（2026-09-29 新增）**

起因是用户报「手机开着代理就明显发热」。用一份真实的 `PacketTunnel` 日志（3 分 53 秒）反算后，
发现**模块层和 IPv6、HTTPS 解密都不是主因，DNS 才是**：

| 项目 | 上游原值 | 现在 | 依据 |
|---|---|---|---|
| `dns-server` 上游数量 | 4 个（2 DoH + 2 UDP） | **2 个**（1 DoH + 1 UDP） | 手册 §通用参数：「DNS 覆写支持同时添加多个地址，Shadowrocket 采用**并行查询**的方式进行解析请求，最先返回的结果将被采用」。实测 **68 个逻辑查询 → 182 次请求（放大 2.68 倍）**，20 个查询同时打满 4 家 |
| DoH 的 HTTP/3 | 自动升级 | **`#no-h3` 关闭** | 手册同段：「有些 `dns over https` 支持 `http3`，所以将会尝试查询，如果支持就切换到 `http3`，可在 doh 链接后面加上 `#no-h3` 关闭」。实测日志里 `dns over quic …#h3` 反复 `ERR_IDLE_CLOSE`，每次重连 = QUIC 握手 + TLS 握手 |

上游原值以注释形式保留在 `[General]` 段里，便于回溯：

```
# 上游原值：dns-server = https://doh.pub/dns-query,https://dns.alidns.com/dns-query,223.5.5.5,119.29.29.29
dns-server = https://doh.pub/dns-query#no-h3,223.5.5.5
```

**刻意不动的**（避免过度调参、也避免把用户没要求的策略强塞进去）：

- `ipv6` —— 实测 `AAAA` 只占 DNS 请求的 **2.2%**（`prefer-ipv6 = false` 时不主动查 AAAA），
  关它收益很小。想关在 UI 里点掉即可。
- `fallback-dns-server` / `hijack-dns` / `block-quic` / `dns-direct-*` —— 保持上游设计意图。

⚠️ 一并记下**当时的误判，免得以后重犯**：最初凭手册推断「`ipv6 = true` 导致每次解析白发 AAAA 查询」，
把它列为耗电方向之一；实测把它推翻了。**日志能定量的事，不要靠推断下结论。**

### 怎么改

`scripts/build_divert.py` 里四个开关：

| 常量 | 作用 |
|---|---|
| `KEEP_GLOBAL = False` | 改成 `True`，Global 那条也会被修好（多下 ~556 KB） |
| `EXPECT_DOMAIN_LIST` | 哪个组有 `_Domain.list`。**探测结果与之冲突时报错，而不是静默少补一条** —— 这正是本次要治的病，不能让它换个地方复发 |
| `TUNE_DNS = True` | 是否做 `[General]` 的 DNS 调优。改成 `False` 则完全不动 `[General]`，`dns-server` 保持上游原值 |
| `DNS_SERVER_OVERRIDE` | 本档写进去的 `dns-server`。**每个 `https://` 项都必须带 `#no-h3`** —— 用 `UPSTREAM_DNS_BASELINE` 记录上游原值，上游一旦改动会告警而不是静默覆盖 |

### 自检（6 组断言，任一不过即非零退出、不提交）

1. 生效行里 Quantumult X 引用必须为 0；
2. `[General]` / `[Proxy Group]` / `[Rule]` 三段必须在；
3. **`[Proxy]` 段必须为空** —— 本仓库是公开的，上游哪天把节点信息塞进来必须拦住；
4. 生效行不得出现节点协议 scheme 或 `password=` / `uuid=` 等凭据字段
   （**只看生效行**：上游 `[Proxy]` 段的文档注释里满是 `password=密码` 这类格式说明，把注释算进去会全线误报）；
5. 被改写的 `X.list` 必须可达；`X_Domain.list` 的存在性必须与期望表一致；
6. `dns-server` 必须**整行等于** `DNS_SERVER_OVERRIDE`，且该常量的每个 DoH 项都带 `#no-h3`
   （整行比对拦不到「改常量时忘了加 `#no-h3`」，所以常量本身要单独自检）。

本地跑：

```bash
python3 scripts/build_divert.py            # 重建
python3 scripts/build_divert.py --check    # 只校验是否与磁盘一致（幂等，忽略生成时间那行）
```

由 `.github/workflows/divert.yml` 每日重建。**刻意与 `build.yml` 分开**：
分流配置和反广告模块是两件不相干的事，上游哪天改了目录结构导致这边断言失败，
不应该连带把每天的反广告规则更新一起停掉。两者共用 `concurrency: repo-write` 串行化，不会抢写。

