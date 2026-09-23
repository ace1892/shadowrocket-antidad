# shadowrocket-antidad

小火箭（Shadowrocket）反广告模块 · 自持整合版

把三个上游规则源整合成**一个模块、一个链接、一份白名单**，托管在自己的仓库里，链接不依赖第三方模块仓库是否改名、停更或归档。

另附一个 **URL 级整合档**（需要开 HTTPS 解密，不打算开就别装）：

- `antidad-rewrite.module` —— ★ **所有 URL 级去广告一个模块搞定**：App 开屏 + 知乎 + B站 + 微信公众号，**26 个解密目标、0 个 CDN**。见第七节。

**日常只需要两个模块**：

```
antidad-full.module      域名级 · 38 万条域名 · 0 解密
antidad-rewrite.module   URL 级 · 全部 App 内去广告 · 26 解密
```

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
| 域名级 | **整合版**（推荐） | `antidad-full.module` | anti-AD + blackmatrix7 域名集 + 关键词/IP，约 38 万域名 | **0** | 默认选择。双源互补，覆盖最广 |
| 域名级 | 轻量版 | `antidad-lite.module` | blackmatrix7 AdvertisingLite ×2，约 3.8 万 | **0** | 省流量、少误杀 |
| 域名级 | 严格版 | `antidad-strict.module` | 整合版 + LOWERTOP AntiAD | **0** | ⚠️ 额外拦遥测/推送域，**会误杀**，见第五节 |
| URL 级 | **重写整合**（推荐） | `antidad-rewrite.module` | App开屏 + 知乎 + B站 + 微信公众号，**全部内联** | **26** | ⭐ 主力。所有 URL 级去广告只装这一个 |
| URL 级 | 开屏（子集） | `antidad-splash.module` | 仅 `antidad-rewrite` 里的 App 开屏部分 | 10 | 只要开屏、不碰 B站脚本 |
| URL 级 | 知乎（子集） | `antidad-zhihu.module` | 仅 `antidad-rewrite` 里的知乎部分 | 7 | 只想去知乎广告、解密面要最小 |

**为什么整合版要做双源**：anti-AD 与 blackmatrix7 域名集的交集只有 **1,926 条**，两边加起来去重后是 **382,242 条**。也就是说这两份名单几乎不重合 —— 只装一份会漏掉一大半。

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

HTTPS 把请求切成「域名 + 加密路径」两段，**域名级规则只看得到域名那一段**，所以 `antidad-full.module` 里那 38 万条域名规则在原理上就拦不到它们。要拦只能解密后按路径匹配 —— 这就是这一档存在的原因。

顺带说明：自建库的域名集里含 "zhihu" 的只有 4 条，且**全是误匹配**（`.bozhihua.com`、`.sibozhihui-lc.com`、`.zhihu.xmcimg.com`、`.zhihuiduijian.com`），一条都不管用。

### 规则为什么是「内联」而不是远程引用

`source.json` 里这条源的 `kind` 是 `INLINE` —— 13 条规则**原文嵌在模块里**，不写 `RULE-SET,<url>`。

理由就是本文第一节说的那件事：上游 blackmatrix7 会重组目录，本项目已经因为「模块引用上游文件被删」吃过一次亏（第三方知乎模块 404 静默死亡）。这套规则自 2025-06 未变更、总共 1.3 KB，内联进来可彻底消除 404 风险；代价是上游真更新时不会自动跟随，需要手动更新 `sources.json` 里的 `rules` 再重新构建。

**`verify.py` 仍然每天盯着它** —— 上游文件条数下降超 15% 或字节缩水超 30% 会开 issue。看到 `zhihu-inline` 报漂移，就是官方改了规则，需要人工同步一次。

### 解密范围（`[MITM]`）

```
hostname = %APPEND% api.zhihu.com,www.zhihu.com,zhuanlan.zhihu.com,103.41.167.226,103.41.167.234,103.41.167.235,103.41.167.236
```

- `%APPEND%` 表示**追加**，不会覆盖其它模块或配置里已声明的解密域名
- 三个域名对应规则里的 `api.zhihu.com` / `www.zhihu.com` / `zhuanlan.zhihu.com`
- 四个 IP 是官方规则特意列的 —— 知乎有**走 IP 直连的广告接口**，只按域名解密会漏

> 官方配套的 `ZhihuAds_MITM.sgmodule` 只声明了 `api.zhihu.com` 和 `zhuanlan.zhihu.com`，**漏了 `www.zhihu.com`**，而规则里 3 条用到了它。本模块已补上。

### 装它的前提与代价

**13 条规则里，5 条不需要解密就生效，8 条必须解密：**

| 规则类型 | 条数 | 需要 MITM？ | 拦什么 |
|---|---|---|---|
| `DOMAIN` | 3 | ❌ 不需要 | `appcloud2.in.zhihu.com`、`mqtt.zhihu.com`、`sugar.zhihu.com` |
| `IP-CIDR` | 2 | ❌ 不需要 | 知乎广告服务器的 IP + IPv6 |
| `URL-REGEX` | 7 | ✅ **需要** | 开屏 `launch_v2`、banner、品牌卡片、相关推荐 |
| `USER-AGENT` | 1 | ✅ **需要** | `AVOS*`（知乎系的旧 UA）|

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

一个模块收齐所有 URL 级去广告，**全部内联**（不远程引用规则集，只有脚本还用上游 JS）：

| 来源 | 条数 | 目标段 | 覆盖内容 |
|---|---|---|---|
| App 开屏 | 9 | `[URL Rewrite]` | 闲鱼 / 高德地图 / 百度地图 / 京东 / 美团 / 拼多多 / 小红书 的开屏接口 |
| B站 URL 重写 | 10 | `[URL Rewrite]` | 开屏 / 搜索默认词 / 首页活动 / 会员购物料 / 播放页小卡片 / 相关推荐 / 大家都在搜 / 动态话题 / 漫画页 |
| 知乎 | 13 | `[Rule]` | `DOMAIN` + `IP-CIDR` + 8 条 `URL-REGEX`（来自 blackmatrix7 官方 ZhihuAds） |
| B站 脚本 | 9 | `[Script]` | 观影页 / 开屏预加载 / 热搜发现 / 推荐流 / 追番 / 直播 / 动态 / Proto / 动态广告 |
| 微信公众号 脚本 | 1 | `[Script]` | 文章底部广告（`mp/getappmsgad`） |

**为什么要合并**：装三个模块时，解密面是三者之和，而且**你看不见它**。
合成一个模块后，`[MITM]` 是一份可审计的名单，`check_mitm.py` 也能一次校验到位。

### 解密目标 26 个

```
App开屏(10)  acs.m.taobao.com  m*.amap.com  newclient.map.baidu.com
             api.m.jd.com  bdsp-x.jd.com  dsp-x.jd.com  wmapi.meituan.com
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
| 解密目标 | 153 | **26** |
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
| 京东 | `api.m.jd.com`（`functionId=start` / `queryMaterialAdverts`）+ `(bdsp-x\|dsp-x).jd.com/adx/` |
| 美团 | `wmapi.meituan.com/api/v\d/startpicture` |
| 拼多多 | `api.(pinduoduo\|yangkeduo).com/api/cappuccino/splash` |
| 小红书 | `www.xiaohongshu.com/api/sns/v\d/system_service/splash_config` |

> **淘宝不在覆盖范围内**：NoAd 原档里 `acs.m.taobao.com` 那 3 条分别是**闲鱼**（`mtop.taobao.idle.*`）、
> **飞猪**（`mtop.trip.*`）、**淘票票**（`mtop.film.*`），都不是淘宝 App 本身 —— 淘宝没有可用的开屏接口规则。

### 规则为什么内联

这些接口路径由 App 自己的代码决定，**多年不变**。内联之后与上游彻底脱钩，
上游怎么改都影响不到本模块。真有一天某条广告回来了，说明那条接口变了，改一行重新构建即可。

**换句话说：不需要跟着上游更新。**

**唯一的例外是 `[Script]`**：脚本 JS 有 27~107 KB，无法内联，只能 `script-path` 远程引用 ——
上游删文件就会静默失效。`verify.py` 会每天探活这三个地址。

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
├── whitelist.txt                # ← 改这个
├── sources.json                 # ← 上游登记表 + 实测基线，改这个（section 字段决定规则落到哪个段）
├── scripts/
│   ├── build.py                 # 由 whitelist + sources 生成 modules
│   ├── verify.py                # 校验上游可达性、内容漂移、以及 script-path 是否还活着
│   └── check_mitm.py            # 校验每条 URL 级规则（含 [Script] 的 pattern）都被 [MITM] 覆盖
├── STATUS.md                    # 自动生成的校验状态，不要手改
└── .github/workflows/
    ├── build.yml                # 改动 whitelist/sources/scripts 时自动重建 + 校验 MITM 覆盖
    └── verify.yml               # 每天 09:00(UTC+8) 校验上游，异常开 issue
```

本地运行（只用标准库，不需要装依赖）：

```bash
python3 scripts/build.py                  # 重建 modules/
python3 scripts/build.py --check          # 只校验是否需要重建
python3 scripts/verify.py                 # 校验上游
python3 scripts/verify.py --update-baseline   # 把当前实测写回 sources.json
python3 scripts/check_mitm.py             # 校验 MITM 覆盖（缺声明=规则静默失效）
```

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
7. 上游规则集含 `URL-REGEX` 类规则，未开 MITM 时不生效（无害，不是 bug）。
8. **上游删路径 → 模块 404 静默死亡**。第三方模块如果引用了 `raw.githubusercontent.com` 或 jsDelivr 的具体文件路径，上游一旦搬目录，模块不会报错，只是**一条规则都不生效**，而 MITM 解密照旧消耗电量。判断方法：把模块里引用的每个 URL 单独 curl 一次看是不是 404。本仓库因此把知乎那 13 条**内联**进模块。
9. **开了 MITM 就必须同时开「HTTPS 解密」并信任根证书**，缺一不可（iOS 还要在「关于本机 → 证书信任设置」手动打开）。三项里缺任何一项，`URL-REGEX` 规则都静默失效。
10. **不要把证书固定的域名放进 `[MITM]`**（银行、支付、证券类）。解密失败会让那些 App **直接连不上网**，比不拦广告糟得多。
11. **`^https?://...` 形态的规则属于 `[URL Rewrite]` 段**，写进 `[Rule]` 段是非法语法（小火箭不会报错，只是不生效）。本仓库用 `sources.json` 的 `section` 字段区分，渲染时自动落到正确的段。
12. **`[MITM]` 漏声明 = 规则静默失效**。规则里出现 `\d`、`\w`、`(a|b)` 交替写法时，肉眼核对极易漏（例如 `m\d\.amap\.com` 必须在 `[MITM]` 写 `m*.amap.com`，`(bdsp-x|dsp-x)\.jd\.com` 必须展开成两条）。用 `scripts/check_mitm.py` 自查，已接入 CI。
13. **判断第三方模块"粗放"还是"精细"，看它的 `[MITM]` 有没有 `-` 排除项**。`-` 前缀表示排除，精细的模块会主动排除高流量 CDN（如 `biliad` 的 `-*cdn*.biliapi.net`）。**没有任何 `-` 排除项的通用模块，会把图片/视频 CDN 一并解密 —— 这是"一开就发热"的主因**，不是规则条数。
14. **MITM 只对"实际访问的域"解密**。声明了 153 个域不等于产生 153 份开销；砍掉你根本不会访问的域省不了电。省电只能靠**砍掉你频繁访问的高流量域**。
15. **规则写错段 = 静默失效**。三种段的语法互不通用：`[Rule]` 收 `DOMAIN,` / `URL-REGEX,` / `RULE-SET,`…；`[URL Rewrite]` 收 `^正则 target`；`[Script]` 收 `名字=type=...,pattern=...,script-path=...`。把 URL 重写规则塞进 `[Rule]`，小火箭**不报错，只是整批忽略**。本仓库用 `sources.json` 的 `section` 字段路由，`build.py` 分段渲染。
16. **`[Script]` 的 `pattern=` 也要 `[MITM]` 覆盖**，漏了同样静默失效 —— 而且更隐蔽：脚本不跑，你不会看到任何报错，只会觉得"广告怎么又回来了"。`check_mitm.py` 已把 `[Script]` 段纳入检查。
17. **正则里的 `(a|b)` 交替在 `[MITM]` 里要展开**。上游 `biliad` 的规则写 `api.(bilibili|biliapi).(com|net)`，展开是 **4 个组合**，但它的 `[MITM]` **只声明了 2 个** —— 另 2 条分支静默失效。本仓库补齐为 4 个（声明天生不会被访问的域，成本为零）。
18. **`[MITM]` 里的 `-` 排除项要排在末尾**。hostname 是「先声明、后排除」，顺序反了排除可能不生效。`build.py` 的 `collect_mitm()` 会自动把 `-` 项统一挪到最后。

---

## 十一、上游来源与实测基线

基线日期 **2026-09-21**：

| 源 | 引用类型 | 条数 | 大小 | 主页 |
|---|---|---|---|---|
| anti-AD 主列表 | DOMAIN-SET | 100,732 | 2.0 MB | [privacy-protection-tools/anti-AD](https://github.com/privacy-protection-tools/anti-AD) |
| blackmatrix7 Advertising（域名集） | DOMAIN-SET | 283,435 | 5.7 MB | [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script) |
| blackmatrix7 Advertising（关键词+IP+正则） | RULE-SET | 781 | 26 KB | 同上 |
| blackmatrix7 AdvertisingLite（域名集） | DOMAIN-SET | 37,692 | 596 KB | 同上 |
| blackmatrix7 AdvertisingLite（关键词+IP） | RULE-SET | 376 | 12.9 KB | 同上 |
| LOWERTOP AntiAD（仅严格档） | RULE-SET | 205 | 8.3 KB | [LOWERTOP/Shadowrocket-First](https://github.com/LOWERTOP/Shadowrocket-First) |
| 知乎广告（仅知乎补丁） | **INLINE** | 13 | 1.3 KB | blackmatrix7 `rewrite/.../ZhihuAssistantPlus/zhihu_plus.sgmodule` |
| App 开屏广告（仅开屏补丁） | **INLINE** | 9 | 803 B | [deezertidal/shadowrocket-rules](https://github.com/deezertidal/shadowrocket-rules) `AdBlock.module` |

规则内容归各上游作者所有，本仓库只做编排、白名单和校验。

> ⚠️ 关于知乎那套规则的现状：blackmatrix7 官方**现存**的知乎模块是
> `rewrite/Shadowrocket/ZhihuAssistant/ZhihuAssistantPlus/zhihu_plus.sgmodule`（即本仓库内联的来源）。
> 而社区里流传的 `script/zhihu/zhihu_plus.js` 路径**已被作者删除**（现为 404），
> `deezertidal/shadowrocket-rules` 的知乎模块至今仍引用那条死链 —— 装它等于纯耗电、
> 零收益，且小火箭不会报错。本仓库内联规则即是为了让这件事不可能再发生在本项目上。

