# shadowrocket-antidad

小火箭（Shadowrocket）反广告模块 · 自持整合版

把三个上游规则源整合成**一个模块、一个链接、一份白名单**，托管在自己的仓库里，链接不依赖第三方模块仓库是否改名、停更或归档。

另附一个**可选补丁** `antidad-zhihu.module`：知乎广告走的是「正经域名下的路径」，域名级规则在原理上拦不到，只能用 URL 正则 —— 这个补丁补的正是这一块，代价是必须开 HTTPS 解密。

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

## 二、三个档位 + 一个可选补丁

| 档位 | 模块文件 | 引用源 | 规则量 | 适用 |
|---|---|---|---|---|
| **整合版**（推荐） | `antidad-full.module` | anti-AD + blackmatrix7 域名集 + 关键词/IP | 约 38 万域名 | 默认选择。双源互补，覆盖最广 |
| **轻量版** | `antidad-lite.module` | blackmatrix7 AdvertisingLite ×2 | 约 3.8 万 | 省流量、少误杀；移动数据为主 |
| **严格版** | `antidad-strict.module` | 整合版 + LOWERTOP AntiAD | 整合版 + 205 条 | ⚠️ 额外拦遥测/推送域，**会误杀**，先读下面第五节 |
| **知乎补丁**（可选） | `antidad-zhihu.module` | 官方 ZhihuAds 13 条，**内联** | 13 条 | ⚠️ **必须开 HTTPS 解密**；只解决知乎一家，见第五节之一 |

**为什么整合版要做双源**：anti-AD 与 blackmatrix7 域名集的交集只有 **1,926 条**，两边加起来去重后是 **382,242 条**。也就是说这两份名单几乎不重合 —— 只装一份会漏掉一大半。

**前三个档位是纯 REJECT，不含 URL 重写和脚本，所以不需要开启 MITM、不用装证书。**

**知乎补丁是唯一需要 MITM 的模块**，原因见第五节之一 —— 不打算开 HTTPS 解密就不要装它，装了只有开销没有收益。

---

## 三、安装

模块地址（四条，前三档任选其一，第四条是可选补丁）：

```
https://cdn.jsdelivr.net/gh/ace1892/shadowrocket-antidad@main/modules/antidad-full.module
https://cdn.jsdelivr.net/gh/ace1892/shadowrocket-antidad@main/modules/antidad-lite.module
https://cdn.jsdelivr.net/gh/ace1892/shadowrocket-antidad@main/modules/antidad-strict.module
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

## 七、仓库结构与自动化

```
.
├── modules/                     # 生成产物，不要手改
│   ├── antidad-full.module
│   ├── antidad-lite.module
│   ├── antidad-strict.module
│   └── antidad-zhihu.module     # 含 [MITM]，需开 HTTPS 解密
├── whitelist.txt                # ← 改这个
├── sources.json                 # ← 上游登记表 + 实测基线，改这个
├── scripts/
│   ├── build.py                 # 由 whitelist + sources 生成 modules
│   └── verify.py                # 校验上游可达性与内容漂移
├── STATUS.md                    # 自动生成的校验状态，不要手改
└── .github/workflows/
    ├── build.yml                # 改动 whitelist/sources 时自动重建模块
    └── verify.yml               # 每天 09:00(UTC+8) 校验上游，异常开 issue
```

本地运行（只用标准库，不需要装依赖）：

```bash
python3 scripts/build.py                  # 重建 modules/
python3 scripts/build.py --check          # 只校验是否需要重建
python3 scripts/verify.py                 # 校验上游
python3 scripts/verify.py --update-baseline   # 把当前实测写回 sources.json
```

**漂移检测怎么判**：规则集每天更新，内容哈希必然变，所以不用哈希当判据。`verify.py` 用「条数」和「字节数」双指标 —— 条数下降超过 15%、或字节缩水超过 30%，就判定异常并开 issue。这能抓到上游被清空、换格式、或不可达。

---

## 八、设计取舍

**Q：为什么不把规则集直接存进仓库，彻底不依赖上游？**

A：代价大于收益。存进来约 7.7 MB（双源并集），Git 会随每日更新膨胀；而且上游本来就在每天更新，自己搬运反而更容易变旧。**当前方案唯一的依赖是上游规则集的 URL 不变**，而 blackmatrix7（8 年、规则集被大量配置引用）和 anti-AD 都极其稳定。`verify.py` 每天盯着，真出问题会开 issue。

如果以后确实需要完全自主，可以加一条 workflow 把上游合并后推到 `dist` 分支，把模块指向自己的 `dist` —— 现有的 `build.py` 数据结构已经为此留好了位置。

**Q：为什么只做了知乎的 URL 重写，不做开屏广告 / 其他 App？**

A：刻意克制。那类规则要覆盖 100+ App，通常意味着 MITM 名单扩大到 150～240 个域名、外加十几条第三方 JavaScript 脚本 —— 而**模块里的脚本能看到被解密的流量**。收益与风险不成比例。

知乎这一档是个例外，理由充分：官方 `ZhihuAds` 是**纯规则、零脚本**（13 条，其中 7 条 URL 正则），解密范围只有 7 个目标，是「最小可行 MITM」。其他 App 请单独装经过审查的现成模块，并按需逐个评估。

**Q：为什么用 jsDelivr 而不是 raw.githubusercontent.com？**

A：实测 `raw.githubusercontent.com` 在本机**间歇性不通**（同一次测试中一条 200、一条 000），`cdn.jsdelivr.net` 全部 200 含大文件。代价是 jsDelivr 的 `@分支` 引用有最长约 12 小时缓存 —— 规则集不需要实时，可接受；但**不要**用它测「刚改完的东西生效了没」。

---

## 九、已知坑

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

---

## 十、上游来源与实测基线

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

规则内容归各上游作者所有，本仓库只做编排、白名单和校验。

> ⚠️ 关于知乎那套规则的现状：blackmatrix7 官方**现存**的知乎模块是
> `rewrite/Shadowrocket/ZhihuAssistant/ZhihuAssistantPlus/zhihu_plus.sgmodule`（即本仓库内联的来源）。
> 而社区里流传的 `script/zhihu/zhihu_plus.js` 路径**已被作者删除**（现为 404），
> `deezertidal/shadowrocket-rules` 的知乎模块至今仍引用那条死链 —— 装它等于纯耗电、
> 零收益，且小火箭不会报错。本仓库内联规则即是为了让这件事不可能再发生在本项目上。

