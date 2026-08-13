# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: production-p0-modules.spec.ts >> 体育平台 生产 P0 功能用例 → UI 自动化（只读） >> P0-UI-001 首页：Live Matches/搜索/REGISTER + 核心 API 资产
- Location: specs\production-p0-modules.spec.ts:59:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText(/REGISTER|Register/i).first()
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for getByText(/REGISTER|Register/i).first()

```

```yaml
- alert
- banner:
  - link "Camel Live":
    - /url: /
    - img "Camel Live"
  - searchbox "Matches Team Competitions News"
  - link "Download":
    - /url: https://play.google.com/store/apps/details?id=com.camelrn&hl=en
    - text: APP
  - tooltip "Scan the QR code to download Camel Live APP":
    - img
    - paragraph: Scan the QR code to download Camel Live APP
  - button "English":
    - img "English"
  - link "FAQ":
    - /url: /my/faq
    - img "FAQ"
  - link "Camel Live":
    - /url: /my/user
    - img "Camel Live"
  - button "menu"
- navigation "breadcrumb":
  - list:
    - listitem:
      - link "Camel Live":
        - /url: /
    - listitem:
      - heading "Football Today - Watch Live Streaming, Soccer Score, Fixtures & Results" [level=1]
- link "https://livecdn.cameltv.live/common/pic/20260810/3673f9674fc94ab3a1446259152ff376.png?width=1888&height=200":
  - /url: https://www.camel1.tv/news/detail/European-Top-Clubs-Friendly-Matche-Kick-Off-Time-FREE-Live-Streamingg-1?entry_way=news&u=MTEwMjU3Mjg%3D
  - img "https://livecdn.cameltv.live/common/pic/20260810/3673f9674fc94ab3a1446259152ff376.png?width=1888&height=200"
- link "https://livecdn.cameltv.live/common/pic/20260813/122ccfc7b1ff4797ba1cbe68a923d989.png?width=1888&height=200":
  - /url: https://www.camel1.tv/news/detail/FA-Community-Shield-Man-City-Arsenal-Free-Live-Stream-Kick-Off-Time-1?entry_way=news&u=MTEwMjU3Mjg%3D
  - img "https://livecdn.cameltv.live/common/pic/20260813/122ccfc7b1ff4797ba1cbe68a923d989.png?width=1888&height=200"
- link "https://livecdn.cameltv.live/common/pic/20260717/25dcfc5210be4a43b828e8ca2d50e718.png?width=1888&height=200&imageView2/0/w/q/70/format/webp":
  - /url: https://take-look.com/v853b0rqv?u=MTEwMjU3Mjg%3D
  - img "https://livecdn.cameltv.live/common/pic/20260717/25dcfc5210be4a43b828e8ca2d50e718.png?width=1888&height=200&imageView2/0/w/q/70/format/webp"
- button "Live Matches":
  - heading "Live Matches" [level=2]
- button "Favorites"
- button "Competitions"
- link "Watch the match and see the score between Rangers F.C. and Jagiellonia Bialystok on 2026-08-14 in the UEFA Europa League.":
  - /url: /football/rangers-f-c-vs-jagiellonia-bialystok/6ypq3nhv9233md7
- time: 08.14 02:30
- link "UEFA Europa League":
  - /url: /r/league/UEFA%20Europa%20League
- img "Rangers F.C."
- text: Rangers F.C.
- img "Jagiellonia Bialystok"
- text: Jagiellonia Bialystok
- link "Watch the match and see the score between Anderlecht and PAOK Saloniki on 2026-08-14 in the UEFA Europa League.":
  - /url: /football/anderlecht-vs-paok-saloniki/dj2ryohlowl4q1z
- time: 08.14 02:30
- link "UEFA Europa League":
  - /url: /r/league/UEFA%20Europa%20League
- img "Anderlecht"
- text: Anderlecht
- img "PAOK Saloniki"
- text: PAOK Saloniki
- link "Watch the match and see the score between Heart of Midlothian F.C. and Benfica on 2026-08-14 in the UEFA Europa League.":
  - /url: /football/heart-of-midlothian-f-c-vs-benfica/318q66hxe9xvqo9
- time: 08.14 02:45
- link "UEFA Europa League":
  - /url: /r/league/UEFA%20Europa%20League
- img "Heart of Midlothian F.C."
- text: Heart of Midlothian F.C.
- img "Benfica"
- text: Benfica
- link "Watch the match and see the score between Santos Fc - SP and Macara on 2026-08-14 in the CONMEBOL Copa Sudamericana.":
  - /url: /football/santos-fc-sp-vs-macara/965mkyhkvv29r1g
- time: 08.14 06:00
- link "CONMEBOL Copa Sudamericana":
  - /url: /league/CONMEBOL%20Copa%20Sudamericana
- img "Santos Fc - SP"
- text: Santos Fc - SP
- img "Macara"
- text: Macara
- link "Watch the match and see the score between CA Rosario Central and Corinthians - SP on 2026-08-14 in the CONMEBOL Copa Libertadores.":
  - /url: /football/ca-rosario-central-vs-corinthians-sp/jw2r09hkzw46rz8
- time: 08.14 08:30
- link "CONMEBOL Copa Libertadores":
  - /url: /league/CONMEBOL%20Copa%20Libertadores
- img "CA Rosario Central"
- text: CA Rosario Central
- img "Corinthians - SP"
- text: Corinthians - SP
- button:
  - img
- button:
  - img
- button "LIVE"
- button:
  - img
- text: Today
- button:
  - img
- link "International Club Friendly International Club Friendly":
  - /url: /league/International%20Club%20Friendly
  - img "International Club Friendly"
  - heading "International Club Friendly" [level=3]
- link "Watch the match and see the score between Arconatese and AC Leon Monza Brianza on 2026-08-13 in the International Club Friendly, with the current score being 0 - 0.":
  - /url: /football/arconatese-vs-ac-leon-monza-brianza/animation/1l4rjnh9wdvvm7v
- time: 17:00
- text: 16'
- link "Arconatese":
  - /url: /team/Arconatese/y0or5jhe4x4qwzv
  - img "Arconatese"
- link "Arconatese":
  - /url: /team/Arconatese/y0or5jhe4x4qwzv
  - heading "Arconatese" [level=4]
- link "AC Leon Monza Brianza":
  - /url: /team/AC%20Leon%20Monza%20Brianza/zp5rzghpnz5q82w
  - img "AC Leon Monza Brianza"
- link "AC Leon Monza Brianza":
  - /url: /team/AC%20Leon%20Monza%20Brianza/zp5rzghpnz5q82w
  - heading "AC Leon Monza Brianza" [level=4]
- img "Live"
- text: LIVE 23 0 0
- link "Watch the match and see the score between AGSM Verona Women and Parma Women on 2026-08-13 in the International Club Friendly, with the current score being 1 - 1.":
  - /url: /football/agsm-verona-women-vs-parma-women/animation/965mkyhk60lvr1g
- time: 17:00
- text: 19'
- link "AGSM Verona Women":
  - /url: /team/AGSM%20Verona%20Women/4jwq2gh4g39m0ve
  - img "AGSM Verona Women"
- link "AGSM Verona Women":
  - /url: /team/AGSM%20Verona%20Women/4jwq2gh4g39m0ve
  - heading "AGSM Verona Women" [level=4]
- link "Parma Women":
  - /url: /team/Parma%20Women/y39mp1h11k9mojx
  - img "Parma Women"
- link "Parma Women":
  - /url: /team/Parma%20Women/y39mp1h11k9mojx
  - heading "Parma Women" [level=4]
- img "Live"
- text: LIVE 27 1 1
- link "Watch the match and see the score between UM-Damansara United and Perak FC on 2026-08-13 in the International Club Friendly, with the current score being 1 - 0.":
  - /url: /football/um-damansara-united-vs-perak-fc/animation/ednm9whw3467ryo
- time: 17:10
- text: 10'
- link "UM-Damansara United":
  - /url: /team/UM-Damansara%20United/l7oqdeh1822r510
  - img "UM-Damansara United"
- link "UM-Damansara United":
  - /url: /team/UM-Damansara%20United/l7oqdeh1822r510
  - heading "UM-Damansara United" [level=4]
- link "Perak FC":
  - /url: /team/Perak%20FC/l7oqdehnjjxr510
  - img "Perak FC"
- link "Perak FC":
  - /url: /team/Perak%20FC/l7oqdehnjjxr510
  - heading "Perak FC" [level=4]
- img "Live"
- text: LIVE 1 0
- link "Guizhou Ziyun \"Wufeng Cup\" Football Tournament Guizhou Ziyun \"Wufeng Cup\" Football Tournament":
  - /url: /league/Guizhou%20Ziyun%20%22Wufeng%20Cup%22%20Football%20Tournament
  - img "Guizhou Ziyun \"Wufeng Cup\" Football Tournament"
  - heading "Guizhou Ziyun \"Wufeng Cup\" Football Tournament" [level=3]
- link "Watch the match and see the score between Lan Yue and Halftime Brothers on 2026-08-13 in the Guizhou Ziyun \"Wufeng Cup\" Football Tournament, with the current score being 5 - 1.":
  - /url: /football/lan-yue-vs-halftime-brothers/live/ednm9whw3l62ryo
- time: 16:00
- text: 69'
- link "Lan Yue":
  - /url: /team/Lan%20Yue/dn1m1gh1jd1moep
  - img "Lan Yue"
- link "Lan Yue":
  - /url: /team/Lan%20Yue/dn1m1gh1jd1moep
  - heading "Lan Yue" [level=4]
- link "Halftime Brothers":
  - /url: /team/Halftime%20Brothers/1l4rjnhe7pvm7vx
  - img "Halftime Brothers"
- link "Halftime Brothers":
  - /url: /team/Halftime%20Brothers/1l4rjnhe7pvm7vx
  - heading "Halftime Brothers" [level=4]
- img "Live"
- text: LIVE 99 5 1
- link "Indian Regional Cup Indian Regional Cup":
  - /url: /league/Indian%20Regional%20Cup
  - img "Indian Regional Cup"
  - heading "Indian Regional Cup" [level=3]
- link "Watch the match and see the score between Aizawl FC and Chanmari FC on 2026-08-13 in the Indian Regional Cup, with the current score being 0 - 0.":
  - /url: /football/aizawl-fc-vs-chanmari-fc/animation/zp5rzghgl9jpq82
- time: 16:30
- text: 21'
- link "Aizawl FC":
  - /url: /team/Aizawl%20FC/3glrw7hw5zwqdyj
  - img "Aizawl FC"
- link "Aizawl FC":
  - /url: /team/Aizawl%20FC/3glrw7hw5zwqdyj
  - heading "Aizawl FC" [level=4]
- link "Chanmari FC":
  - /url: /team/Chanmari%20FC/318q66h01wzqo9j
  - img "Chanmari FC"
- link "Chanmari FC":
  - /url: /team/Chanmari%20FC/318q66h01wzqo9j
  - heading "Chanmari FC" [level=4]
- img "Live"
- text: LIVE 20 0 0
- link "Slovak U19 A Slovak U19 A":
  - /url: /league/Slovak%20U19%20A
  - heading "Slovak U19 A" [level=3]
- link "Watch the match and see the score between DAC Dunajska Streda U19 and FK Zeleziarne Podbrezova U19 on 2026-08-13 in the Slovak U19 A, with the current score being 0 - 0.":
  - /url: /football/dac-dunajska-streda-u19-vs-fk-zeleziarne-podbrezova-u19/animation/4wyrn4h6k1ndq86
- time: 17:00
- text: 18'
- link "DAC Dunajska Streda U19":
  - /url: /team/DAC%20Dunajska%20Streda%20U19/dn1m1gh4xgdmoep
- link "DAC Dunajska Streda U19":
  - /url: /team/DAC%20Dunajska%20Streda%20U19/dn1m1gh4xgdmoep
  - heading "DAC Dunajska Streda U19" [level=4]
- link "FK Zeleziarne Podbrezova U19":
  - /url: /team/FK%20Zeleziarne%20Podbrezova%20U19/y39mp1hj321mojx
- link "FK Zeleziarne Podbrezova U19":
  - /url: /team/FK%20Zeleziarne%20Podbrezova%20U19/y39mp1hj321mojx
  - heading "FK Zeleziarne Podbrezova U19" [level=4]
- img "Live"
- text: LIVE 8 0 0
- link "UEFA Europa League UEFA Europa League":
  - /url: /r/league/UEFA%20Europa%20League
  - heading "UEFA Europa League" [level=3]
- link "Watch the match and see the score between Pafos FC and Red Bull Salzburg on 2026-08-14 in the UEFA Europa League.":
  - /url: /football/pafos-fc-vs-red-bull-salzburg/23xmvkh65e81qg8
- time: 01:00
- text: NS
- link "Pafos FC":
  - /url: /team/Pafos%20FC/2y8m4zh8ln5ql07
- link "Pafos FC":
  - /url: /team/Pafos%20FC/2y8m4zh8ln5ql07
  - heading "Pafos FC" [level=4]
- link "Red Bull Salzburg":
  - /url: /team/Red%20Bull%20Salzburg/p3glrw7he0gqdyj
- link "Red Bull Salzburg":
  - /url: /team/Red%20Bull%20Salzburg/p3glrw7he0gqdyj
  - heading "Red Bull Salzburg" [level=4]
- link "Watch the match and see the score between Gornik Zabrze and Ferencvarosi TC on 2026-08-14 in the UEFA Europa League.":
  - /url: /football/gornik-zabrze-vs-ferencvarosi-tc/dn1m1ghlj5l3moe
- time: 01:00
- text: NS
- link "Gornik Zabrze":
  - /url: /team/Gornik%20Zabrze/p4jwq2ghd29m0ve
- link "Gornik Zabrze":
  - /url: /team/Gornik%20Zabrze/p4jwq2ghd29m0ve
  - heading "Gornik Zabrze" [level=4]
- link "Ferencvarosi TC":
  - /url: /team/Ferencvarosi%20TC/vl7oqdehzwpr510
- link "Ferencvarosi TC":
  - /url: /team/Ferencvarosi%20TC/vl7oqdehzwpr510
  - heading "Ferencvarosi TC" [level=4]
- link "Watch the match and see the score between Omonia Nicosia FC and Lincoln Red Imps FC on 2026-08-14 in the UEFA Europa League.":
  - /url: /football/omonia-nicosia-fc-vs-lincoln-red-imps-fc/ednm9whwnj71ryo
- time: 01:00
- text: NS
- link "Omonia Nicosia FC":
  - /url: /team/Omonia%20Nicosia%20FC/kjw2r09hy41rz84
- link "Omonia Nicosia FC":
  - /url: /team/Omonia%20Nicosia%20FC/kjw2r09hy41rz84
  - heading "Omonia Nicosia FC" [level=4]
- link "Lincoln Red Imps FC":
  - /url: /team/Lincoln%20Red%20Imps%20FC/y39mp1h5kzpmojx
- link "Lincoln Red Imps FC":
  - /url: /team/Lincoln%20Red%20Imps%20FC/y39mp1h5kzpmojx
  - heading "Lincoln Red Imps FC" [level=4]
- link "Watch the match and see the score between Besiktas JK and FC Hradec Králové on 2026-08-14 in the UEFA Europa League.":
  - /url: /football/besiktas-jk-vs-fc-hradec-kralove/l7oqdehgpvgdr51
- time: 01:00
- text: NS
- link "Besiktas JK":
  - /url: /team/Besiktas%20JK/gy0or5jhdpgqwzv
- link "Besiktas JK":
  - /url: /team/Besiktas%20JK/gy0or5jhdpgqwzv
  - heading "Besiktas JK" [level=4]
- link "FC Hradec Králové":
  - /url: /team/FC%20Hradec%20Kr%C3%A1lov%C3%A9/3glrw7hwjyjqdyj
- link "FC Hradec Králové":
  - /url: /team/FC%20Hradec%20Kr%C3%A1lov%C3%A9/3glrw7hwjyjqdyj
  - heading "FC Hradec Králové" [level=4]
- link "Watch the match and see the score between CS Universitatea Craiova and KuPs on 2026-08-14 in the UEFA Europa League.":
  - /url: /football/cs-universitatea-craiova-vs-kups/x7lm7phj6lz2m2w
- time: 01:00
- text: NS
- link "CS Universitatea Craiova":
  - /url: /team/CS%20Universitatea%20Craiova/zp5rzghjeodq82w
- link "CS Universitatea Craiova":
  - /url: /team/CS%20Universitatea%20Craiova/zp5rzghjeodq82w
  - heading "CS Universitatea Craiova" [level=4]
- link "KuPs":
  - /url: /team/KuPs/z318q66hp13qo9j
- link "KuPs":
  - /url: /team/KuPs/z318q66hp13qo9j
  - heading "KuPs" [level=4]
- link "Watch the match and see the score between Vikingur Reykjavik and Thun on 2026-08-14 in the UEFA Europa League.":
  - /url: /football/vikingur-reykjavik-vs-thun/3glrw7hn8x74qdy
- time: 01:30
- text: NS
- link "Vikingur Reykjavik":
  - /url: /team/Vikingur%20Reykjavik/vjxm8gh4jldr6od
- link "Vikingur Reykjavik":
  - /url: /team/Vikingur%20Reykjavik/vjxm8gh4jldr6od
  - heading "Vikingur Reykjavik" [level=4]
- link "Thun":
  - /url: /team/Thun/gpxwrxlhoekryk0
- link "Thun":
  - /url: /team/Thun/gpxwrxlhoekryk0
  - heading "Thun" [level=4]
- link "Watch the match and see the score between KI Klaksvik and Lech Poznan on 2026-08-14 in the UEFA Europa League.":
  - /url: /football/ki-klaksvik-vs-lech-poznan/y39mp1h6lx63moj
- time: 01:30
- text: NS
- link "KI Klaksvik":
  - /url: /team/KI%20Klaksvik/965mkyh7j77r1ge
- link "KI Klaksvik":
  - /url: /team/KI%20Klaksvik/965mkyh7j77r1ge
  - heading "KI Klaksvik" [level=4]
- link "Lech Poznan":
  - /url: /team/Lech%20Poznan/p4jwq2ghj25m0ve
- link "Lech Poznan":
  - /url: /team/Lech%20Poznan/p4jwq2ghj25m0ve
  - heading "Lech Poznan" [level=4]
- link "Watch the match and see the score between CSKA Sofia and Maccabi Tel Aviv on 2026-08-14 in the UEFA Europa League.":
  - /url: /football/cska-sofia-vs-maccabi-tel-aviv/l5ergph41z4pr8k
- time: 02:00
- text: NS
- link "CSKA Sofia":
  - /url: /team/CSKA%20Sofia/j1l4rjnhp05m7vx
- link "CSKA Sofia":
  - /url: /team/CSKA%20Sofia/j1l4rjnhp05m7vx
  - heading "CSKA Sofia" [level=4]
- link "Maccabi Tel Aviv":
  - /url: /team/Maccabi%20Tel%20Aviv/9vjxm8gh649r6od
- link "Maccabi Tel Aviv":
  - /url: /team/Maccabi%20Tel%20Aviv/9vjxm8gh649r6od
  - heading "Maccabi Tel Aviv" [level=4]
- link "Watch the match and see the score between Rangers F.C. and Jagiellonia Bialystok on 2026-08-14 in the UEFA Europa League.":
  - /url: /football/rangers-f-c-vs-jagiellonia-bialystok/6ypq3nhv9233md7
- time: 02:30
- text: NS
- link "Rangers F.C.":
  - /url: /team/Rangers%20F.C./kdj2ryoh0ydq1zp
- link "Rangers F.C.":
  - /url: /team/Rangers%20F.C./kdj2ryoh0ydq1zp
  - heading "Rangers F.C." [level=4]
- link "Jagiellonia Bialystok":
  - /url: /team/Jagiellonia%20Bialystok/8y39mp1h8l6mojx
- link "Jagiellonia Bialystok":
  - /url: /team/Jagiellonia%20Bialystok/8y39mp1h8l6mojx
  - heading "Jagiellonia Bialystok" [level=4]
- link "Watch the match and see the score between Anderlecht and PAOK Saloniki on 2026-08-14 in the UEFA Europa League.":
  - /url: /football/anderlecht-vs-paok-saloniki/dj2ryohlowl4q1z
- time: 02:30
- text: NS
- link "Anderlecht":
  - /url: /team/Anderlecht/kdj2ryoh3ozq1zp
- link "Anderlecht":
  - /url: /team/Anderlecht/kdj2ryoh3ozq1zp
  - heading "Anderlecht" [level=4]
- link "PAOK Saloniki":
  - /url: /team/PAOK%20Saloniki/v2y8m4zhy8vql07
- link "PAOK Saloniki":
  - /url: /team/PAOK%20Saloniki/v2y8m4zhy8vql07
  - heading "PAOK Saloniki" [level=4]
- link "Watch the match and see the score between Heart of Midlothian F.C. and Benfica on 2026-08-14 in the UEFA Europa League.":
  - /url: /football/heart-of-midlothian-f-c-vs-benfica/318q66hxe9xvqo9
- time: 02:45
- text: NS
- link "Heart of Midlothian F.C.":
  - /url: /team/Heart%20of%20Midlothian%20F.C./yl5ergphj82r8k0
- link "Heart of Midlothian F.C.":
  - /url: /team/Heart%20of%20Midlothian%20F.C./yl5ergphj82r8k0
  - heading "Heart of Midlothian F.C." [level=4]
- link "Benfica":
  - /url: /team/Benfica/z8yomo4hjyoq0j6
- link "Benfica":
  - /url: /team/Benfica/z8yomo4hjyoq0j6
  - heading "Benfica" [level=4]
- link "Watch the match and see the score between Egnatia and Shamrock Rovers on 2026-08-14 in the UEFA Europa League.":
  - /url: /football/egnatia-vs-shamrock-rovers/4wyrn4h63j6vq86
- time: 03:00
- text: NS
- link "Egnatia":
  - /url: /team/Egnatia/2y8m4zh37p5ql07
- link "Egnatia":
  - /url: /team/Egnatia/2y8m4zh37p5ql07
  - heading "Egnatia" [level=4]
- link "Shamrock Rovers":
  - /url: /team/Shamrock%20Rovers/4zp5rzghengq82w
- link "Shamrock Rovers":
  - /url: /team/Shamrock%20Rovers/4zp5rzghengq82w
  - heading "Shamrock Rovers" [level=4]
- link "International Club Friendly International Club Friendly":
  - /url: /league/International%20Club%20Friendly
  - heading "International Club Friendly" [level=3]
- link "Watch the match and see the score between Athletic Club Boise and Sporting FC on 2026-08-13 in the International Club Friendly, with the current score being 2 - 0.":
  - /url: /football/athletic-club-boise-vs-sporting-fc/ednm9whw3p8yryo
- time: 09:30
- text: FT
- link "Athletic Club Boise":
  - /url: /team/Athletic%20Club%20Boise/dn1m1gh1gygmoep
- link "Athletic Club Boise":
  - /url: /team/Athletic%20Club%20Boise/dn1m1gh1gygmoep
  - heading "Athletic Club Boise" [level=4]
- link "Sporting FC":
  - /url: /team/Sporting%20FC/4wyrn4he536q86p
- link "Sporting FC":
  - /url: /team/Sporting%20FC/4wyrn4he536q86p
  - heading "Sporting FC" [level=4]
- text: 2 0
- link "Watch the match and see the score between Como 1907 (W) and Genoa Women on 2026-08-13 in the International Club Friendly.":
  - /url: /football/como-1907-w-vs-genoa-women/y39mp1h62n1dmoj
- time: 16:30
- text: TBD
- link "Como 1907 (W)":
  - /url: /team/Como%201907%20(W)/x7lm7phpzz4m2wd
- link "Como 1907 (W)":
  - /url: /team/Como%201907%20(W)/x7lm7phpzz4m2wd
  - heading "Como 1907 (W)" [level=4]
- link "Genoa Women":
  - /url: /team/Genoa%20Women/k82rekh33p5repz
- link "Genoa Women":
  - /url: /team/Genoa%20Women/k82rekh33p5repz
  - heading "Genoa Women" [level=4]
- link "Watch the match and see the score between Shakhtar Donetsk Women and FC Kryvbas Kriviy Rih Women on 2026-08-13 in the International Club Friendly.":
  - /url: /football/shakhtar-donetsk-women-vs-fc-kryvbas-kriviy-rih-women/k82rekhg743erep
- time: 18:00
- text: NS
- link "Shakhtar Donetsk Women":
  - /url: /team/Shakhtar%20Donetsk%20Women/dn1m1gh868xmoep
- link "Shakhtar Donetsk Women":
  - /url: /team/Shakhtar%20Donetsk%20Women/dn1m1gh868xmoep
  - heading "Shakhtar Donetsk Women" [level=4]
- link "FC Kryvbas Kriviy Rih Women":
  - /url: /team/FC%20Kryvbas%20Kriviy%20Rih%20Women/x7lm7phwz92m2wd
- link "FC Kryvbas Kriviy Rih Women":
  - /url: /team/FC%20Kryvbas%20Kriviy%20Rih%20Women/x7lm7phwz92m2wd
  - heading "FC Kryvbas Kriviy Rih Women" [level=4]
- link "Watch the match and see the score between Bali United and Sabah FC on 2026-08-13 in the International Club Friendly.":
  - /url: /football/bali-united-vs-sabah-fc/318q66hx5dlkqo9
- time: 20:00
- text: NS
- link "Bali United":
  - /url: /team/Bali%20United/dn1m1ghe757moep
- link "Bali United":
  - /url: /team/Bali%20United/dn1m1ghe757moep
  - heading "Bali United" [level=4]
- link "Sabah FC":
  - /url: /team/Sabah%20FC/4jwq2gh4kz2m0ve
- link "Sabah FC":
  - /url: /team/Sabah%20FC/4jwq2gh4kz2m0ve
  - heading "Sabah FC" [level=4]
- link "Watch the match and see the score between Deportivo La Coruna Women and FC Porto (W) on 2026-08-13 in the International Club Friendly.":
  - /url: /football/deportivo-la-coruna-women-vs-fc-porto-w/dn1m1ghlwz8dmoe
- time: 22:00
- text: NS
- link "Deportivo La Coruna Women":
  - /url: /team/Deportivo%20La%20Coruna%20Women/l7oqdeh6k97r510
- link "Deportivo La Coruna Women":
  - /url: /team/Deportivo%20La%20Coruna%20Women/l7oqdeh6k97r510
  - heading "Deportivo La Coruna Women" [level=4]
- link "FC Porto (W)":
  - /url: /team/FC%20Porto%20(W)/dn1m1gh11x9moep
- link "FC Porto (W)":
  - /url: /team/FC%20Porto%20(W)/dn1m1gh11x9moep
  - heading "FC Porto (W)" [level=4]
- link "Watch the match and see the score between ASO Chlef and Kazma on 2026-08-13 in the International Club Friendly.":
  - /url: /football/aso-chlef-vs-kazma/jw2r09hkod80rz8
- time: 22:00
- text: NS
- link "ASO Chlef":
  - /url: /team/ASO%20Chlef/4zp5rzgh8xvq82w
- link "ASO Chlef":
  - /url: /team/ASO%20Chlef/4zp5rzgh8xvq82w
  - heading "ASO Chlef" [level=4]
- link "Kazma":
  - /url: /team/Kazma/n54qllh2d7pqvy9
- link "Kazma":
  - /url: /team/Kazma/n54qllh2d7pqvy9
  - heading "Kazma" [level=4]
- link "Watch the match and see the score between Al Khaldiya and Al-Salmiya on 2026-08-13 in the International Club Friendly.":
  - /url: /football/al-khaldiya-vs-al-salmiya/l7oqdehg5z78r51
- time: 22:00
- text: NS
- link "Al Khaldiya":
  - /url: /team/Al%20Khaldiya/dj2ryohg20wq1zp
- link "Al Khaldiya":
  - /url: /team/Al%20Khaldiya/dj2ryohg20wq1zp
  - heading "Al Khaldiya" [level=4]
- link "Al-Salmiya":
  - /url: /team/Al-Salmiya/dn1m1gh484vmoep
- link "Al-Salmiya":
  - /url: /team/Al-Salmiya/dn1m1gh484vmoep
  - heading "Al-Salmiya" [level=4]
- link "Watch the match and see the score between Bologna W and Arezzo W on 2026-08-13 in the International Club Friendly.":
  - /url: /football/bologna-w-vs-arezzo-w/23xmvkh6njwwqg8
- time: 23:00
- text: NS
- link "Bologna W":
  - /url: /team/Bologna%20W/pxwrxlhzln8ryk0
- link "Bologna W":
  - /url: /team/Bologna%20W/pxwrxlhzln8ryk0
  - heading "Bologna W" [level=4]
- link "Arezzo W":
  - /url: /team/Arezzo%20W/3glrw7hzo18qdyj
- link "Arezzo W":
  - /url: /team/Arezzo%20W/3glrw7hzo18qdyj
  - heading "Arezzo W" [level=4]
- link "Watch the match and see the score between Ternana W and Frosinone (W) on 2026-08-13 in the International Club Friendly.":
  - /url: /football/ternana-w-vs-frosinone-w/4wyrn4h6knvnq86
- time: 23:00
- text: NS
- link "Ternana W":
  - /url: /team/Ternana%20W/4wyrn4hvvk8q86p
- link "Ternana W":
  - /url: /team/Ternana%20W/4wyrn4hvvk8q86p
  - heading "Ternana W" [level=4]
- link "Frosinone (W)":
  - /url: /team/Frosinone%20(W)/3glrw7ho75lqdyj
- link "Frosinone (W)":
  - /url: /team/Frosinone%20(W)/3glrw7ho75lqdyj
  - heading "Frosinone (W)" [level=4]
- link "Watch the match and see the score between SD Laredo and Suodu Pei on 2026-08-13 in the International Club Friendly.":
  - /url: /football/sd-laredo-vs-suodu-pei/vjxm8ghez6v6r6o
- time: 23:00
- text: NS
- link "SD Laredo":
  - /url: /team/SD%20Laredo/n54qllhe13nqvy9
- link "SD Laredo":
  - /url: /team/SD%20Laredo/n54qllhe13nqvy9
  - heading "SD Laredo" [level=4]
- link "Suodu Pei":
  - /url: /team/Suodu%20Pei/vjxm8ghgpe0r6od
- link "Suodu Pei":
  - /url: /team/Suodu%20Pei/vjxm8ghgpe0r6od
  - heading "Suodu Pei" [level=4]
- link "Watch the match and see the score between Reggina and Sanremese on 2026-08-13 in the International Club Friendly.":
  - /url: /football/reggina-vs-sanremese/4wyrn4h6k1pdq86
- time: 23:30
- text: NS
- link "Reggina":
  - /url: /team/Reggina/8y39mp1hnngmojx
- link "Reggina":
  - /url: /team/Reggina/8y39mp1hnngmojx
  - heading "Reggina" [level=4]
- link "Sanremese":
  - /url: /team/Sanremese/y39mp1h399pmojx
- link "Sanremese":
  - /url: /team/Sanremese/y39mp1h399pmojx
  - heading "Sanremese" [level=4]
- link "Watch the match and see the score between A.S.D. Giugliano Calcio 1928 and Ischia Isolaverde on 2026-08-13 in the International Club Friendly.":
  - /url: /football/a-s-d-giugliano-calcio-1928-vs-ischia-isolaverde/ednm9whw3l8kryo
- time: 23:30
- text: NS
- link "A.S.D. Giugliano Calcio 1928":
  - /url: /team/A.S.D.%20Giugliano%20Calcio%201928/8yomo4h7510q0j6
- link "A.S.D. Giugliano Calcio 1928":
  - /url: /team/A.S.D.%20Giugliano%20Calcio%201928/8yomo4h7510q0j6
  - heading "A.S.D. Giugliano Calcio 1928" [level=4]
- link "Ischia Isolaverde":
  - /url: /team/Ischia%20Isolaverde/4jwq2gh4j7pm0ve
- link "Ischia Isolaverde":
  - /url: /team/Ischia%20Isolaverde/4jwq2gh4j7pm0ve
  - heading "Ischia Isolaverde" [level=4]
- link "Watch the match and see the score between AS FAR Rabat and Chabab Atlas Khenifra on 2026-08-14 in the International Club Friendly.":
  - /url: /football/as-far-rabat-vs-chabab-atlas-khenifra/2y8m4zh5kdl5ql0
- time: 00:00
- text: NS
- link "AS FAR Rabat":
  - /url: /team/AS%20FAR%20Rabat/3glrw7hwkgzqdyj
- link "AS FAR Rabat":
  - /url: /team/AS%20FAR%20Rabat/3glrw7hwkgzqdyj
  - heading "AS FAR Rabat" [level=4]
- link "Chabab Atlas Khenifra":
  - /url: /team/Chabab%20Atlas%20Khenifra/zp5rzghjn42q82w
- link "Chabab Atlas Khenifra":
  - /url: /team/Chabab%20Atlas%20Khenifra/zp5rzghjn42q82w
  - heading "Chabab Atlas Khenifra" [level=4]
- link "Watch the match and see the score between Olympique de Beja and CS Sfaxien on 2026-08-14 in the International Club Friendly.":
  - /url: /football/olympique-de-beja-vs-cs-sfaxien/8yomo4h1dj9nq0j
- time: 00:00
- text: NS
- link "Olympique de Beja":
  - /url: /team/Olympique%20de%20Beja/dj2ryohkv9vq1zp
- link "Olympique de Beja":
  - /url: /team/Olympique%20de%20Beja/dj2ryohkv9vq1zp
  - heading "Olympique de Beja" [level=4]
- link "CS Sfaxien":
  - /url: /team/CS%20Sfaxien/9vjxm8ghdlpr6od
- link "CS Sfaxien":
  - /url: /team/CS%20Sfaxien/9vjxm8ghdlpr6od
  - heading "CS Sfaxien" [level=4]
- link "Watch the match and see the score between Kalaa Sport and Progres Sakiet Eddaier on 2026-08-14 in the International Club Friendly.":
  - /url: /football/kalaa-sport-vs-progres-sakiet-eddaier/dj2ryohlz381q1z
- time: 00:00
- text: NS
- link "Kalaa Sport":
  - /url: /team/Kalaa%20Sport/23xmvkho3e0qg8n
- link "Kalaa Sport":
  - /url: /team/Kalaa%20Sport/23xmvkho3e0qg8n
  - heading "Kalaa Sport" [level=4]
- link "Progres Sakiet Eddaier":
  - /url: /team/Progres%20Sakiet%20Eddaier/l5ergph3x4zr8k0
- link "Progres Sakiet Eddaier":
  - /url: /team/Progres%20Sakiet%20Eddaier/l5ergph3x4zr8k0
  - heading "Progres Sakiet Eddaier" [level=4]
- link "Watch the match and see the score between AE Kifisias and Niki Volou on 2026-08-14 in the International Club Friendly.":
  - /url: /football/ae-kifisias-vs-niki-volou/jw2r09hkod49rz8
- time: 00:00
- text: NS
- link "AE Kifisias":
  - /url: /team/AE%20Kifisias/n54qllhxx1gqvy9
- link "AE Kifisias":
  - /url: /team/AE%20Kifisias/n54qllhxx1gqvy9
  - heading "AE Kifisias" [level=4]
- link "Niki Volou":
  - /url: /team/Niki%20Volou/pxwrxlhg95wryk0
- link "Niki Volou":
  - /url: /team/Niki%20Volou/pxwrxlhg95wryk0
  - heading "Niki Volou" [level=4]
- link "Watch the match and see the score between Panserraikos and PAOK Saloniki B on 2026-08-14 in the International Club Friendly.":
  - /url: /football/panserraikos-vs-paok-saloniki-b/l5ergph49j02r8k
- time: 00:00
- text: NS
- link "Panserraikos":
  - /url: /team/Panserraikos/zp5rzghjxneq82w
- link "Panserraikos":
  - /url: /team/Panserraikos/zp5rzghjxneq82w
  - heading "Panserraikos" [level=4]
- link "PAOK Saloniki B":
  - /url: /team/PAOK%20Saloniki%20B/dj2ryohgwxeq1zp
- link "PAOK Saloniki B":
  - /url: /team/PAOK%20Saloniki%20B/dj2ryohgwxeq1zp
  - heading "PAOK Saloniki B" [level=4]
- link "Watch the match and see the score between L'Aquila and ASD Grassina on 2026-08-14 in the International Club Friendly.":
  - /url: /football/l-aquila-vs-asd-grassina/vjxm8ghezoder6o
- time: 00:30
- text: NS
- link "L'Aquila":
  - /url: /team/L'Aquila/gx7lm7phye3m2wd
- link "L'Aquila":
  - /url: /team/L'Aquila/gx7lm7phye3m2wd
  - heading "L'Aquila" [level=4]
- link "ASD Grassina":
  - /url: /team/ASD%20Grassina/3glrw7hj8o9qdyj
- link "ASD Grassina":
  - /url: /team/ASD%20Grassina/3glrw7hj8o9qdyj
  - heading "ASD Grassina" [level=4]
- link "Watch the match and see the score between Racing de Ferrol and Real Aviles on 2026-08-14 in the International Club Friendly.":
  - /url: /football/racing-de-ferrol-vs-real-aviles/4jwq2ghn3doom0v
- time: 01:00
- text: NS
- link "Racing de Ferrol":
  - /url: /team/Racing%20de%20Ferrol/kdj2ryoh3xeq1zp
- link "Racing de Ferrol":
  - /url: /team/Racing%20de%20Ferrol/kdj2ryoh3xeq1zp
  - heading "Racing de Ferrol" [level=4]
- link "Real Aviles":
  - /url: /team/Real%20Aviles/vjxm8gh4e55r6od
- link "Real Aviles":
  - /url: /team/Real%20Aviles/vjxm8gh4e55r6od
  - heading "Real Aviles" [level=4]
- link "Watch the match and see the score between CD Derio and SD San Ignacio on 2026-08-14 in the International Club Friendly.":
  - /url: /football/cd-derio-vs-sd-san-ignacio/8yomo4h1djnyq0j
- time: 01:00
- text: NS
- link "CD Derio":
  - /url: /team/CD%20Derio/dj2ryohgon0q1zp
- link "CD Derio":
  - /url: /team/CD%20Derio/dj2ryohgon0q1zp
  - heading "CD Derio" [level=4]
- link "SD San Ignacio":
  - /url: /team/SD%20San%20Ignacio/ednm9whz26xryox
- link "SD San Ignacio":
  - /url: /team/SD%20San%20Ignacio/ednm9whz26xryox
  - heading "SD San Ignacio" [level=4]
- link "Watch the match and see the score between Amurrio and SD Beasain on 2026-08-14 in the International Club Friendly.":
  - /url: /football/amurrio-vs-sd-beasain/zp5rzghgl914q82
- time: 01:00
- text: NS
- link "Amurrio":
  - /url: /team/Amurrio/v2y8m4zhkw4ql07
- link "Amurrio":
  - /url: /team/Amurrio/v2y8m4zhkw4ql07
  - heading "Amurrio" [level=4]
- link "SD Beasain":
  - /url: /team/SD%20Beasain/1l4rjnh1k83m7vx
- link "SD Beasain":
  - /url: /team/SD%20Beasain/1l4rjnh1k83m7vx
  - heading "SD Beasain" [level=4]
- link "Watch the match and see the score between Hercules and Valencia CF on 2026-08-14 in the International Club Friendly.":
  - /url: /football/hercules-vs-valencia-cf/6ypq3nhvjde6md7
- time: 01:30
- text: NS
- link "Hercules":
  - /url: /team/Hercules/1l4rjnh61e5m7vx
- link "Hercules":
  - /url: /team/Hercules/1l4rjnh61e5m7vx
  - heading "Hercules" [level=4]
- link "Valencia CF":
  - /url: /team/Valencia%20CF/56ypq3nhd2lmd7o
- link "Valencia CF":
  - /url: /team/Valencia%20CF/56ypq3nhd2lmd7o
  - heading "Valencia CF" [level=4]
- button "Show more arrow":
  - text: Show more
  - img "arrow"
- link "Match Replays":
  - /url: /match-replay
  - heading "Match Replays" [level=3]
- list:
  - listitem:
    - 'link "2026-07-19 2026 FIFA World Cup Final: England vs. France 2026-07-19 2026 FIFA World Cup Final: England vs. France"':
      - /url: /match-replay/107123464706493798
      - 'img "2026-07-19 2026 FIFA World Cup Final: England vs. France"'
      - text: "2026-07-19 2026 FIFA World Cup Final: England vs. France"
  - listitem:
    - 'link "2026-07-16 2026 FIFA World Cup Semifinal: England vs. Argentina 2026-07-16 2026 FIFA World Cup Semifinal: England vs. Argentina"':
      - /url: /match-replay/107123464706493799
      - 'img "2026-07-16 2026 FIFA World Cup Semifinal: England vs. Argentina"'
      - text: "2026-07-16 2026 FIFA World Cup Semifinal: England vs. Argentina"
  - listitem:
    - 'link "2026-07-15 2026 FIFA World Cup Semifinal: France vs. Spain 2026-07-15 2026 FIFA World Cup Semifinal: France vs. Spain"':
      - /url: /match-replay/107123464706493800
      - 'img "2026-07-15 2026 FIFA World Cup Semifinal: France vs. Spain"'
      - text: "2026-07-15 2026 FIFA World Cup Semifinal: France vs. Spain"
  - listitem:
    - 'link "2026-07-19 2026 FIFA World Cup Third Place Playoff: France vs. England 2026-07-19 2026 FIFA World Cup Third Place Playoff: France vs. England"':
      - /url: /match-replay/107123464706493811
      - 'img "2026-07-19 2026 FIFA World Cup Third Place Playoff: France vs. England"'
      - text: "2026-07-19 2026 FIFA World Cup Third Place Playoff: France vs. England"
  - listitem:
    - 'link "2026-07-12 2026 FIFA World Cup Quarterfinal: Argentina vs. Switzerland 2026-07-12 2026 FIFA World Cup Quarterfinal: Argentina vs. Switzerland"':
      - /url: /match-replay/107123464706493848
      - 'img "2026-07-12 2026 FIFA World Cup Quarterfinal: Argentina vs. Switzerland"'
      - text: "2026-07-12 2026 FIFA World Cup Quarterfinal: Argentina vs. Switzerland"
- link "Show more arrow":
  - /url: /match-replay
  - text: Show more
  - img "arrow"
- link "FIFA World Cup 26":
  - /url: /worldcup-2026
  - heading "FIFA World Cup 2026 Free Streaming, Live Scores, Fixtures, Groups, Schedule & Bracket FIFA World Cup 2026" [level=2]:
    - text: FIFA World Cup 2026 Free Streaming, Live Scores, Fixtures, Groups, Schedule & Bracket
    - img "FIFA World Cup 2026"
- link "Free Football Live Streaming":
  - /url: /free-football-live-streaming
  - text: Free Football Live Streaming Watch today's live football matches free, with real-time scores, fixtures and stats.
- text: Favorites
- heading "All News" [level=2]
- text: FIFA World Cup Match Preview Transfer Market Premier League Champions League In-depth Article Prediction Other Match News Today In History Winter Transfer
- 'link "How to Watch FA Community Shield Man City vs Arsenal: Free Live Stream & Kick-Off Time 5 hours ago icon_like_uncheck 26 TOP"':
  - /url: /news/detail/FA-Community-Shield-Man-City-Arsenal-Free-Live-Stream-Kick-Off-Time-1?entry_way=news
  - 'heading "How to Watch FA Community Shield Man City vs Arsenal: Free Live Stream & Kick-Off Time" [level=3]'
  - time: 5 hours ago
  - img "icon_like_uncheck"
  - text: 26 TOP
- 'link "How to Watch European Top Clubs Friendly Matches : Kick-Off Time & FREE Live Streaming ALL in Preview 21 hours ago icon_like_uncheck 11665 TOP"':
  - /url: /news/detail/European-Top-Clubs-Friendly-Matche-Kick-Off-Time-FREE-Live-Streamingg-1?entry_way=news
  - 'heading "How to Watch European Top Clubs Friendly Matches : Kick-Off Time & FREE Live Streaming ALL in Preview" [level=3]'
  - time: 21 hours ago
  - img "icon_like_uncheck"
  - text: 11665 TOP
- 'link "As the Fireworks Fade, the Passion Endures: Full HD Replays of the 2026 World Cup Are Officially Live! 2026-07-30 icon_like_uncheck 9620 TOP"':
  - /url: /news/detail/world-cup-camellive-match-replays-spain-argentina-rodri-1?entry_way=news
  - 'heading "As the Fireworks Fade, the Passion Endures: Full HD Replays of the 2026 World Cup Are Officially Live!" [level=3]'
  - time: 2026-07-30
  - img "icon_like_uncheck"
  - text: 9620 TOP
- 'link "How to Watch PSG vs Aston Villa: Free Live Stream & Kick-Off Time 21 hours ago icon_like_uncheck 5582"':
  - /url: /news/detail/UEFA-Super-Cup-Paris-Saint-Germain-Aston-Villa-Team-News-Kick-Off-Time-1?entry_way=news
  - 'heading "How to Watch PSG vs Aston Villa: Free Live Stream & Kick-Off Time" [level=3]'
  - time: 21 hours ago
  - img "icon_like_uncheck"
  - text: "5582"
- 'link "Only one‑year after joining: Monaco seeks to terminate contract with 33‑year‑old Paul Pogba a day ago icon_like_uncheck 17"':
  - /url: /news/detail/Paul%E2%80%91Pogba%E2%80%91Monaco%E2%80%91contract%E2%80%91termination%E2%80%91Fabrizio%E2%80%91Romano%E2%80%91summer%E2%80%91transfer%E2%80%91window%E2%80%91pre%E2%80%91season%E2%80%91injury-1?entry_way=news
  - 'heading "Only one‑year after joining: Monaco seeks to terminate contract with 33‑year‑old Paul Pogba" [level=3]'
  - time: a day ago
  - img "icon_like_uncheck"
  - text: "17"
- 'link "Iker Casillas on Mourinho’s mole‑hunt: He screamed and shouted at us like he had gone crazy a day ago icon_like_uncheck 17"':
  - /url: /news/detail/Iker%E2%80%91Casillas%E2%80%91Jos%C3%A9%E2%80%91Mourinho%E2%80%91Real%E2%80%91Madrid%E2%80%91mole%E2%80%91hunt%E2%80%91Netflix%E2%80%91documentary%E2%80%91Rui%E2%80%91Faria-1?entry_way=news
  - 'heading "Iker Casillas on Mourinho’s mole‑hunt: He screamed and shouted at us like he had gone crazy" [level=3]'
  - time: a day ago
  - img "icon_like_uncheck"
  - text: "17"
- link "Cristiano Ronaldo announces his marriage to Georgina via social media a day ago icon_like_uncheck 19":
  - /url: /news/detail/Cristiano%E2%80%91Ronaldo%E2%80%91Georgina%E2%80%91Rodr%C3%ADguez%E2%80%91social%E2%80%91media%E2%80%91wedding%E2%80%91marriage%E2%80%91proposal-1?entry_way=news
  - heading "Cristiano Ronaldo announces his marriage to Georgina via social media" [level=3]
  - time: a day ago
  - img "icon_like_uncheck"
  - text: "19"
- 'link "Napoli’s saga comes to an end: 33‑year‑old Romelu Lukaku joins Fenerbahçe 2 days ago icon_like_uncheck 23"':
  - /url: /news/detail/Romelu%E2%80%91Lukaku%E2%80%91Napoli%E2%80%91Fenerbah%C3%A7e%E2%80%91Fabrizio%E2%80%91Romano%E2%80%91transfer%E2%80%91fee%E2%80%91Belgium%E2%80%91national%E2%80%91team-1?entry_way=news
  - 'heading "Napoli’s saga comes to an end: 33‑year‑old Romelu Lukaku joins Fenerbahçe" [level=3]'
  - time: 2 days ago
  - img "icon_like_uncheck"
  - text: "23"
- 'link "Champions League Qualifiers 2nd Leg: Free Live Stream & Schedule 2 days ago icon_like_uncheck 1571"':
  - /url: /news/detail/Champions-League-3rd-Qualifying-Round-First-Leg-Kick-Off-Time-FREE-Live-Streaming-1?entry_way=news
  - 'heading "Champions League Qualifiers 2nd Leg: Free Live Stream & Schedule" [level=3]'
  - time: 2 days ago
  - img "icon_like_uncheck"
  - text: "1571"
- 'link "Persib Bandung’s 2026/2027 BRI Super League Schedule: Bandung Tigers Chase Fourth‑Straight League Title! 2 days ago icon_like_uncheck 10"':
  - /url: /news/detail/Persib%E2%80%91Bandung%E2%80%91BRI%E2%80%91Super%E2%80%91League%E2%80%91four%E2%80%91straight%E2%80%91titles%E2%80%91Bojan%E2%80%91Hodak%E2%80%91AFC%E2%80%91Champions%E2%80%91League%E2%80%91Two%E2%80%91match%E2%80%911?entry_way=news
  - 'heading "Persib Bandung’s 2026/2027 BRI Super League Schedule: Bandung Tigers Chase Fourth‑Straight League Title!" [level=3]'
  - time: 2 days ago
  - img "icon_like_uncheck"
  - text: "10"
- 'link "Alvarez’s transfer falls through: Atletico Madrid dressing‑room believes he should admit fault and apologise 2 days ago icon_like_uncheck 12"':
  - /url: /news/detail/Julian%E2%80%91Alvarez%E2%80%91Atletico%E2%80%91Madrid%E2%80%91transfer%E2%80%91saga%E2%80%91dressing%E2%80%91room%E2%80%91public%E2%80%91apology%E2%80%91Barcelona-1?entry_way=news
  - 'heading "Alvarez’s transfer falls through: Atletico Madrid dressing‑room believes he should admit fault and apologise" [level=3]'
  - time: 2 days ago
  - img "icon_like_uncheck"
  - text: "12"
- 'link "€55 million buy‑out option: Barcelona captain Ronald Araujo joins Liverpool 2 days ago icon_like_uncheck 29"':
  - /url: /news/detail/Ronald%E2%80%91Araujo%E2%80%91Liverpool%E2%80%91Barcelona%E2%80%91loan%E2%80%91transfer%E2%80%91buy%E2%80%91out%E2%80%91clause%E2%80%91Uruguay-1?entry_way=news
  - 'heading "€55 million buy‑out option: Barcelona captain Ronald Araujo joins Liverpool" [level=3]'
  - time: 2 days ago
  - img "icon_like_uncheck"
  - text: "29"
- 'link "Set to Wear Number 14 Jersey for the New Season: Neither Rashford nor Manchester United Are Keen to Push Through a Transfer 3 days ago icon_like_uncheck 31"':
  - /url: /news/detail/Marcus-Rashford-Manchester-United-Michael-Carrick-Barcelona-transfer-window-pre%E2%80%91season-1?entry_way=news
  - 'heading "Set to Wear Number 14 Jersey for the New Season: Neither Rashford nor Manchester United Are Keen to Push Through a Transfer" [level=3]'
  - time: 3 days ago
  - img "icon_like_uncheck"
  - text: "31"
- 'link "Mourinho Recalls Nearly Taking Manchester United Job in 2013: But I Loved Chelsea More 3 days ago icon_like_uncheck 17"':
  - /url: /news/detail/Jose-Mourinho-Manchester-United-Chelsea-Sir-Alex-Ferguson-Netflix-documentary-Real-Madrid-1?entry_way=news
  - 'heading "Mourinho Recalls Nearly Taking Manchester United Job in 2013: But I Loved Chelsea More" [level=3]'
  - time: 3 days ago
  - img "icon_like_uncheck"
  - text: "17"
- 'link "Joint Statement by UEFA, AFC and Concacaf: FIFA Has Not Acknowledged Fundamental Flaws In Its Sale Proposal 3 days ago icon_like_uncheck 12"':
  - /url: /news/detail/UEFA-AFC-Concacaf-FIFA-joint-statement-integrity-1?entry_way=news
  - 'heading "Joint Statement by UEFA, AFC and Concacaf: FIFA Has Not Acknowledged Fundamental Flaws In Its Sale Proposal" [level=3]'
  - time: 3 days ago
  - img "icon_like_uncheck"
  - text: "12"
- link "Transfer Following Impressive World Cup Campaign? Manchester City Reach Personal Agreement With 18‑Year‑Old Morocco Midfielder Ayyoub Bouaddi 3 days ago icon_like_uncheck 29":
  - /url: /news/detail/Manchester-City-Ayyoub-Bouaddi-Lille-Morocco-World-Cup-transfer-1?entry_way=news
  - heading "Transfer Following Impressive World Cup Campaign? Manchester City Reach Personal Agreement With 18‑Year‑Old Morocco Midfielder Ayyoub Bouaddi" [level=3]
  - time: 3 days ago
  - img "icon_like_uncheck"
  - text: "29"
- 'link "Argentina speaks out on FIFA controversy: backs Gianni Infantino for re‑election as FIFA President 6 days ago icon_like_uncheck 62"':
  - /url: /news/detail/Argentine-Football-Association%2CGianni-Infantino%2CFIFA%2CFIFA-President%2Cstatement%2Cglobal-football-1?entry_way=news
  - 'heading "Argentina speaks out on FIFA controversy: backs Gianni Infantino for re‑election as FIFA President" [level=3]'
  - time: 6 days ago
  - img "icon_like_uncheck"
  - text: "62"
- link "Rodri decides to join Barcelona, but Barcelona's first offer gets rejected 6 days ago icon_like_uncheck 95":
  - /url: /news/detail/Rodri%2CBarcelona%2CManchester-City%2Ctransfer-offer%2CReal-Madrid%2Cmidfielder-1?entry_way=news
  - heading "Rodri decides to join Barcelona, but Barcelona's first offer gets rejected" [level=3]
  - time: 6 days ago
  - img "icon_like_uncheck"
  - text: "95"
- 'link "Official: Real Madrid complete contract renewal with 26‑year‑old Vinicius Jr., new deal runs until 2032 6 days ago icon_like_uncheck 52"':
  - /url: /news/detail/Real-Madrid%2CVinicius-Jr.%2Ccontract-renewal%2CLa-Liga%2CUEFA-Champions-League%2CBrazilian-winger-1?entry_way=news
  - 'heading "Official: Real Madrid complete contract renewal with 26‑year‑old Vinicius Jr., new deal runs until 2032" [level=3]'
  - time: 6 days ago
  - img "icon_like_uncheck"
  - text: "52"
- link "How to Watch Emirates Cup Arsenal vs Dortmund :Team News, Kick-Off Time, FREE Live Streaming 6 days ago icon_like_uncheck 2104":
  - /url: /news/detail/Emirates-Cup-Arsenal-Dortmund-Team-News-Kick-Off-Time-1?entry_way=news
  - heading "How to Watch Emirates Cup Arsenal vs Dortmund :Team News, Kick-Off Time, FREE Live Streaming" [level=3]
  - time: 6 days ago
  - img "icon_like_uncheck"
  - text: "2104"
- link "How to Watch Friendly Match Paris Saint-Germain vs Manchester United :Team News, Kick-Off Time, FREE Live Streaming 6 days ago icon_like_uncheck 2085":
  - /url: /news/detail/Friendly-Match-Paris-Saint-Germain-Manchester-United-Team-News-Kick-Off-Time-1?entry_way=news
  - heading "How to Watch Friendly Match Paris Saint-Germain vs Manchester United :Team News, Kick-Off Time, FREE Live Streaming" [level=3]
  - time: 6 days ago
  - img "icon_like_uncheck"
  - text: "2085"
- 'link "Barcelona Join the Race for Rodri: Real Madrid Yet To Settle Transfer Fee 2026-08-06 icon_like_uncheck 63"':
  - /url: /news/detail/Rodri%E2%80%91Barcelona%E2%80%91Real%E2%80%91Madrid%E2%80%91Manchester%E2%80%91City%E2%80%91transfer%E2%80%91pursuit%E2%80%91Frenkie%E2%80%91de%E2%80%91Jong-1?entry_way=news
  - 'heading "Barcelona Join the Race for Rodri: Real Madrid Yet To Settle Transfer Fee" [level=3]'
  - time: 2026-08-06
  - img "icon_like_uncheck"
  - text: "63"
- 'link "Transfer Fee Up To €140 Million: Real Madrid Reach Agreement For Diomande 2026-08-06 icon_like_uncheck 62"':
  - /url: /news/detail/Yan%E2%80%91Diomande%E2%80%91Real%E2%80%91Madrid%E2%80%91RB%E2%80%91Leipzig%E2%80%91transfer%E2%80%91fee%E2%80%91Legan%C3%A9s%E2%80%91Ivorian%E2%80%91international-1?entry_way=news
  - 'heading "Transfer Fee Up To €140 Million: Real Madrid Reach Agreement For Diomande" [level=3]'
  - time: 2026-08-06
  - img "icon_like_uncheck"
  - text: "62"
- 'link "Argentine Journalist Reveals: Three Players Suffered Muscle Strains Before Final, Emiliano Martínez Opposed Scaloni’s Tactics 2026-08-06 icon_like_uncheck 66"':
  - /url: /news/detail/Renzo%E2%80%91Pantich%E2%80%91Emiliano%E2%80%91Mart%C3%ADnez%E2%80%91Lionel%E2%80%91Scaloni%E2%80%91World%E2%80%91Cup%E2%80%91final%E2%80%91Argentina%E2%80%91national%E2%80%91football%E2%80%91team%E2%80%911?entry_way=news
  - 'heading "Argentine Journalist Reveals: Three Players Suffered Muscle Strains Before Final, Emiliano Martínez Opposed Scaloni’s Tactics" [level=3]'
  - time: 2026-08-06
  - img "icon_like_uncheck"
  - text: "66"
- 'link "FIFA Official Statement: Full Backing for Infantino Remains Intact; Attacks Against FIFA Will Not Be Tolerated 2026-08-06 icon_like_uncheck 38"':
  - /url: /news/detail/FIFA-Gianni-Infantino-FIFA-Forward-Enterprise-Rabat-FIFA-Council-member-associations-1?entry_way=news
  - 'heading "FIFA Official Statement: Full Backing for Infantino Remains Intact; Attacks Against FIFA Will Not Be Tolerated" [level=3]'
  - time: 2026-08-06
  - img "icon_like_uncheck"
  - text: "38"
- 'link "How to Watch European Top Clubs Friendly Matches : Kick-Off Time & FREE Live Streaming ALL in Preview 2026-08-05 icon_like_uncheck 6509"':
  - /url: /news/detail/European-Top-Clubs-Friendly-Matches-Kick-Off-Time-FREE-Live-treaming-1?entry_way=news
  - 'heading "How to Watch European Top Clubs Friendly Matches : Kick-Off Time & FREE Live Streaming ALL in Preview" [level=3]'
  - time: 2026-08-05
  - img "icon_like_uncheck"
  - text: "6509"
- 'link "FIFA Faces Crisis: Three Continental Confederations Determined to Oust Gianni Infantino 2026-08-04 icon_like_uncheck 71"':
  - /url: /news/detail/Gianni-Infantino-FIFA-UEFA-CONCACAF-AFC-FIFA-Forward-Enterprise-1?entry_way=news
  - 'heading "FIFA Faces Crisis: Three Continental Confederations Determined to Oust Gianni Infantino" [level=3]'
  - time: 2026-08-04
  - img "icon_like_uncheck"
  - text: "71"
- 'link "Manchester City Delay Negotiations: Hoping Barcelona Join Real Madrid’s Race for Rodri 2026-08-04 icon_like_uncheck 78"':
  - /url: /news/detail/Rodri-Manchester-City-Real-Madrid-Barcelona-Fabrizio-Romano-Frenkie-de-Jong-1?entry_way=news
  - 'heading "Manchester City Delay Negotiations: Hoping Barcelona Join Real Madrid’s Race for Rodri" [level=3]'
  - time: 2026-08-04
  - img "icon_like_uncheck"
  - text: "78"
- link "How to Watch Friendly Match AC Milan vs Inter Milan :Team News, Kick-Off Time, FREE Live Streaming 2026-08-04 icon_like_uncheck 95":
  - /url: /news/detail/Friendly-Match-AC-Milan-Inter-Milan-Team-News-Kick-Off-Time-1?entry_way=news
  - heading "How to Watch Friendly Match AC Milan vs Inter Milan :Team News, Kick-Off Time, FREE Live Streaming" [level=3]
  - time: 2026-08-04
  - img "icon_like_uncheck"
  - text: "95"
- link "How to Watch Friendly Match Chelsea vs Juventus :Team News, Kick-Off Time, FREE Live Streaming 2026-08-04 icon_like_uncheck 362":
  - /url: /news/detail/Friendly-Match-Chelsea-Juventu-Team-News-Kick-Off-Time-1?entry_way=news
  - heading "How to Watch Friendly Match Chelsea vs Juventus :Team News, Kick-Off Time, FREE Live Streaming" [level=3]
  - time: 2026-08-04
  - img "icon_like_uncheck"
  - text: "362"
- text: Show more
- img "arrow"
- contentinfo
- heading "Never Lose Access Again!" [level=2]
- paragraph: Save our official links page to your phone's home screen or bookmarks. No matter how the domain changes, we'll always be there for you.
- link "Visit Official Links Page":
  - /url: https://www.camel1.link
- link "Camel Live Home":
  - /url: /
- paragraph: Camel Live is a streaming application designed for sports enthusiasts, offering high-definition live broadcasting services. You can watch 100% free live soccer/sepak bola/fútbol/futebol streams of over 2,600 matches worldwide, including the UEFA Champions League, English Premier League, La Liga, Serie A, Bundesliga, Ligue 1, FIFA Club World Cup, etc. You can freely pick your favorite matches from various leagues, cups, and tournaments spanning North America, South America, Asia, and Africa to watch completely free of charge. In addition, we deliver a comprehensive range of sports insights based on big data analysis, including match schedules, real-time live scores, half-time/full-time results, goals, assists, yellow/red cards, starting lineups, substitute lists, team updates, historical head-to-head records, and match result predictions.Stream football online free today and never miss a goal!
- paragraph: Our website is secure, stable, and plugin-free, providing fans with comprehensive and timely match information services 24/7. Camel's live broadcast signals are collected by users or aggregated from search engines, and all content is sourced from the Internet. On Camel Live, you can get the latest updates on all football matches!
- link "Download Camel Live on App Store":
  - /url: https://apps.apple.com/us/app/camel-live/id6743193754?l=zh-Hans-CN
  - img "Download Camel Live on App Store"
- link "Get Camel Live on Google Play":
  - /url: https://play.google.com/store/apps/details?id=com.camelrn&hl=en
  - img "Get Camel Live on Google Play"
- text: Next Match
- link "Rangers F.C. VS Jagiellonia Bialystok":
  - /url: /head-to-head/20260814-rangers-f-c-vs-jagiellonia-bialystok
- link "Anderlecht VS PAOK Saloniki":
  - /url: /head-to-head/20260814-anderlecht-vs-paok-saloniki
- link "Heart of Midlothian F.C. VS Benfica":
  - /url: /head-to-head/20260814-heart-of-midlothian-f-c-vs-benfica
- link "Santos Fc - SP VS Macara":
  - /url: /head-to-head/20260814-santos-fc-sp-vs-macara
- link "CA Rosario Central VS Corinthians - SP":
  - /url: /head-to-head/20260814-ca-rosario-central-vs-corinthians-sp
- link "Marseille VS Atletico Madrid":
  - /url: /head-to-head/20260814-marseille-vs-atletico-madrid
- link "Coventry City VS AS Monaco":
  - /url: /head-to-head/20260815-coventry-city-vs-as-monaco
- link "Al Hilal VS Al Faisaly":
  - /url: /head-to-head/20260815-al-hilal-vs-al-faisaly
- link "Galatasaray VS Corum FK":
  - /url: /head-to-head/20260815-galatasaray-vs-corum-fk
- link "Sporting CP VS Vitoria Guimaraes":
  - /url: /head-to-head/20260815-sporting-cp-vs-vitoria-guimaraes
- link "SC Freiburg VS Crystal Palace":
  - /url: /head-to-head/20260815-sc-freiburg-vs-crystal-palace
- link "Chelsea VS Real Sociedad":
  - /url: /head-to-head/20260815-chelsea-vs-real-sociedad
- link "1. FC Union Berlin VS Ipswich Town":
  - /url: /head-to-head/20260815-1-fc-union-berlin-vs-ipswich-town
- link "FC Bayern Munich VS RB Leipzig":
  - /url: /head-to-head/20260815-fc-bayern-munich-vs-rb-leipzig
- link "Borussia Monchengladbach VS Aston Villa":
  - /url: /head-to-head/20260815-borussia-monchengladbach-vs-aston-villa
- link "Union Saint-Gilloise VS Zulte-Waregem":
  - /url: /head-to-head/20260815-union-saint-gilloise-vs-zulte-waregem
- link "Brighton&Hove Albion VS Bologna":
  - /url: /head-to-head/20260815-brighton-hove-albion-vs-bologna
- link "Newcastle United VS Bayer 04 Leverkusen":
  - /url: /head-to-head/20260815-newcastle-united-vs-bayer-04-leverkusen
- link "Sunderland VS Stade Rennais FC":
  - /url: /head-to-head/20260815-sunderland-vs-stade-rennais-fc
- link "Hull City VS OGC Nice":
  - /url: /head-to-head/20260815-hull-city-vs-ogc-nice
- link "Tottenham Hotspur VS TSG Hoffenheim":
  - /url: /head-to-head/20260815-tottenham-hotspur-vs-tsg-hoffenheim
- link "Everton VS LOSC Lille":
  - /url: /head-to-head/20260815-everton-vs-losc-lille
- link "Manchester United VS AC Milan":
  - /url: /head-to-head/20260815-manchester-united-vs-ac-milan
- link "Borussia Dortmund VS AS Roma":
  - /url: /head-to-head/20260815-borussia-dortmund-vs-as-roma
- link "KV Kortrijk VS Royal Antwerp":
  - /url: /head-to-head/20260816-kv-kortrijk-vs-royal-antwerp
- link "Dundee United VS Celtic F.C.":
  - /url: /head-to-head/20260816-dundee-united-vs-celtic-f-c
- link "Inter Milan VS Real Betis":
  - /url: /head-to-head/20260816-inter-milan-vs-real-betis
- link "Al Nassr VS Al Fateh":
  - /url: /head-to-head/20260816-al-nassr-vs-al-fateh
- link "Genclerbirligi VS Fenerbahce":
  - /url: /head-to-head/20260816-genclerbirligi-vs-fenerbahce
- link "Racing Genk VS KVC Westerlo":
  - /url: /head-to-head/20260816-racing-genk-vs-kvc-westerlo
- text: Hot Matches
- link "Live Matches":
  - /url: /match/progressing
- link "Arconatese VS AC Leon Monza Brianza":
  - /url: /football/arconatese-vs-ac-leon-monza-brianza/1l4rjnh9wdvvm7v
- link "AGSM Verona Women VS Parma Women":
  - /url: /football/agsm-verona-women-vs-parma-women/965mkyhk60lvr1g
- link "UM-Damansara United VS Perak FC":
  - /url: /football/um-damansara-united-vs-perak-fc/ednm9whw3467ryo
- link "Lan Yue VS Halftime Brothers":
  - /url: /football/lan-yue-vs-halftime-brothers/ednm9whw3l62ryo
- link "Aizawl FC VS Chanmari FC":
  - /url: /football/aizawl-fc-vs-chanmari-fc/zp5rzghgl9jpq82
- link "DAC Dunajska Streda U19 VS FK Zeleziarne Podbrezova U19":
  - /url: /football/dac-dunajska-streda-u19-vs-fk-zeleziarne-podbrezova-u19/4wyrn4h6k1ndq86
- link "All Hot Matches":
  - /url: /hotmatch
- link "Arconatese VS AC Leon Monza Brianza":
  - /url: /football/arconatese-vs-ac-leon-monza-brianza/1l4rjnh9wdvvm7v
- link "AGSM Verona Women VS Parma Women":
  - /url: /football/agsm-verona-women-vs-parma-women/965mkyhk60lvr1g
- link "UM-Damansara United VS Perak FC":
  - /url: /football/um-damansara-united-vs-perak-fc/ednm9whw3467ryo
- link "Shakhtar Donetsk Women VS FC Kryvbas Kriviy Rih Women":
  - /url: /football/shakhtar-donetsk-women-vs-fc-kryvbas-kriviy-rih-women/k82rekhg743erep
- link "Bali United VS Sabah FC":
  - /url: /football/bali-united-vs-sabah-fc/318q66hx5dlkqo9
- link "Deportivo La Coruna Women VS FC Porto (W)":
  - /url: /football/deportivo-la-coruna-women-vs-fc-porto-w/dn1m1ghlwz8dmoe
- link "ASO Chlef VS Kazma":
  - /url: /football/aso-chlef-vs-kazma/jw2r09hkod80rz8
- link "Al Khaldiya VS Al-Salmiya":
  - /url: /football/al-khaldiya-vs-al-salmiya/l7oqdehg5z78r51
- link "Bologna W VS Arezzo W":
  - /url: /football/bologna-w-vs-arezzo-w/23xmvkh6njwwqg8
- link "Ternana W VS Frosinone (W)":
  - /url: /football/ternana-w-vs-frosinone-w/4wyrn4h6knvnq86
- link "SD Laredo VS Suodu Pei":
  - /url: /football/sd-laredo-vs-suodu-pei/vjxm8ghez6v6r6o
- link "Reggina VS Sanremese":
  - /url: /football/reggina-vs-sanremese/4wyrn4h6k1pdq86
- link "A.S.D. Giugliano Calcio 1928 VS Ischia Isolaverde":
  - /url: /football/a-s-d-giugliano-calcio-1928-vs-ischia-isolaverde/ednm9whw3l8kryo
- link "AS FAR Rabat VS Chabab Atlas Khenifra":
  - /url: /football/as-far-rabat-vs-chabab-atlas-khenifra/2y8m4zh5kdl5ql0
- link "Olympique de Beja VS CS Sfaxien":
  - /url: /football/olympique-de-beja-vs-cs-sfaxien/8yomo4h1dj9nq0j
- link "Kalaa Sport VS Progres Sakiet Eddaier":
  - /url: /football/kalaa-sport-vs-progres-sakiet-eddaier/dj2ryohlz381q1z
- link "AE Kifisias VS Niki Volou":
  - /url: /football/ae-kifisias-vs-niki-volou/jw2r09hkod49rz8
- link "Panserraikos VS PAOK Saloniki B":
  - /url: /football/panserraikos-vs-paok-saloniki-b/l5ergph49j02r8k
- link "L'Aquila VS ASD Grassina":
  - /url: /football/l-aquila-vs-asd-grassina/vjxm8ghezoder6o
- link "Racing de Ferrol VS Real Aviles":
  - /url: /football/racing-de-ferrol-vs-real-aviles/4jwq2ghn3doom0v
- link "CD Derio VS SD San Ignacio":
  - /url: /football/cd-derio-vs-sd-san-ignacio/8yomo4h1djnyq0j
- link "Amurrio VS SD Beasain":
  - /url: /football/amurrio-vs-sd-beasain/zp5rzghgl914q82
- link "Hercules VS Valencia CF":
  - /url: /football/hercules-vs-valencia-cf/6ypq3nhvjde6md7
- link "Muleno CF VS Real Murcia U19":
  - /url: /football/muleno-cf-vs-real-murcia-u19/6ypq3nhvjdx8md7
- link "CD Calasanz de Soria VS Almazan":
  - /url: /football/cd-calasanz-de-soria-vs-almazan/dj2ryohlz33dq1z
- link "Gimnastic de Tarragona VS SD Huesca":
  - /url: /football/gimnastic-de-tarragona-vs-sd-huesca/k82rekhg7jz5rep
- link "Zafra VS Don Benito":
  - /url: /football/zafra-vs-don-benito/l7oqdehg5zy3r51
- link "Atletico de Madrid B VS Mirandes":
  - /url: /football/atletico-de-madrid-b-vs-mirandes/y39mp1h62ev2moj
- link "Chiclana VS Atletico Sanluqueno":
  - /url: /football/chiclana-vs-atletico-sanluqueno/23xmvkh6nj3dqg8
- link "Getafe B VS Rayo Vallecano B":
  - /url: /football/getafe-b-vs-rayo-vallecano-b/6ypq3nhvjo68md7
- link "CF Intercity VS UD Levante B":
  - /url: /football/cf-intercity-vs-ud-levante-b/965mkyhk6944r1g
- link "RSD Alcala Henares VS CF Rayo Majadahonda":
  - /url: /football/rsd-alcala-henares-vs-cf-rayo-majadahonda/l7oqdehg5ky8r51
- link "Tritium VS Solbiatese Arno":
  - /url: /football/tritium-vs-solbiatese-arno/pxwrxlhykop0ryk
- link "Pafos FC VS Red Bull Salzburg":
  - /url: /football/pafos-fc-vs-red-bull-salzburg/23xmvkh65e81qg8
- link "Gornik Zabrze VS Ferencvarosi TC":
  - /url: /football/gornik-zabrze-vs-ferencvarosi-tc/dn1m1ghlj5l3moe
- link "Omonia Nicosia FC VS Lincoln Red Imps FC":
  - /url: /football/omonia-nicosia-fc-vs-lincoln-red-imps-fc/ednm9whwnj71ryo
- link "Besiktas JK VS FC Hradec Králové":
  - /url: /football/besiktas-jk-vs-fc-hradec-kralove/l7oqdehgpvgdr51
- link "CS Universitatea Craiova VS KuPs":
  - /url: /football/cs-universitatea-craiova-vs-kups/x7lm7phj6lz2m2w
- link "Vikingur Reykjavik VS Thun":
  - /url: /football/vikingur-reykjavik-vs-thun/3glrw7hn8x74qdy
- link "KI Klaksvik VS Lech Poznan":
  - /url: /football/ki-klaksvik-vs-lech-poznan/y39mp1h6lx63moj
- link "CSKA Sofia VS Maccabi Tel Aviv":
  - /url: /football/cska-sofia-vs-maccabi-tel-aviv/l5ergph41z4pr8k
- link "Rangers F.C. VS Jagiellonia Bialystok":
  - /url: /football/rangers-f-c-vs-jagiellonia-bialystok/6ypq3nhv9233md7
- link "Anderlecht VS PAOK Saloniki":
  - /url: /football/anderlecht-vs-paok-saloniki/dj2ryohlowl4q1z
- link "Heart of Midlothian F.C. VS Benfica":
  - /url: /football/heart-of-midlothian-f-c-vs-benfica/318q66hxe9xvqo9
- link "Egnatia VS Shamrock Rovers":
  - /url: /football/egnatia-vs-shamrock-rovers/4wyrn4h63j6vq86
- link "Mirassol - SP VS Liga Dep Universitaria Quito":
  - /url: /football/mirassol-sp-vs-liga-dep-universitaria-quito/l5ergph41n08r8k
- link "CA Rosario Central VS Corinthians - SP":
  - /url: /football/ca-rosario-central-vs-corinthians-sp/jw2r09hkzw46rz8
- link "Santos Fc - SP VS Macara":
  - /url: /football/santos-fc-sp-vs-macara/965mkyhkvv29r1g
- link "BSS Sporting Club VS Kidderpore SC":
  - /url: /football/bss-sporting-club-vs-kidderpore-sc/1l4rjnh9wp9nm7v
- link "Bidhannagar MSA VS Mohun Bagan SG II":
  - /url: /football/bidhannagar-msa-vs-mohun-bagan-sg-ii/4jwq2ghn3dnwm0v
- link "George Telegraph FC VS United Kolkata SC":
  - /url: /football/george-telegraph-fc-vs-united-kolkata-sc/zp5rzghgleggq82
- button "Show more arrow":
  - text: Show more
  - img "arrow"
- text: Hot Leagues
- link "FIFA World Cup":
  - /url: /league/FIFA%20World%20Cup
- link "UEFA Champions League":
  - /url: /r/league/UEFA%20Champions%20League
- link "Premier League":
  - /url: /r/league/English%20Premier%20League
- link "La Liga":
  - /url: /r/league/Spanish%20La%20Liga
- link "UEFA Europa League":
  - /url: /r/league/UEFA%20Europa%20League
- link "Ligue 1":
  - /url: /r/league/French%20Ligue%201
- link "UEFA Super Cup":
  - /url: /league/UEFA%20Super%20Cup
- link "International Club Friendly":
  - /url: /league/International%20Club%20Friendly
- link "United States Major League Soccer":
  - /url: /league/United%20States%20Major%20League%20Soccer
- link "Primeira Liga":
  - /url: /r/league/Portuguese%20Primera%20Liga
- link "Belgian Pro League":
  - /url: /league/Belgian%20Pro%20League
- link "Turkish Super League":
  - /url: /r/league/Turkish%20Super%20League
- link "Scottish Premiership":
  - /url: /league/Scottish%20Premiership
- link "Liga 1":
  - /url: /league/Indonesian%20Super%20League
- link "UEFA Nations League":
  - /url: /league/UEFA%20Nations%20League
- link "CONMEBOL Copa Libertadores":
  - /url: /league/CONMEBOL%20Copa%20Libertadores
- link "Brazilian Serie A":
  - /url: /league/Brazilian%20Serie%20A
- link "Argentine Division 1":
  - /url: /league/Argentine%20Division%201
- link "Bundesliga":
  - /url: /r/league/Bundesliga
- link "Serie A":
  - /url: /r/league/Italian%20Serie%20A
- link "UEFA Conference League":
  - /url: /r/league/UEFA%20Europa%20Conference%20League
- link "Saudi Pro League":
  - /url: /r/league/Saudi%20Professional%20League
- link "FIFA World Cup qualification (UEFA)":
  - /url: /league/FIFA%20World%20Cup%20qualification%20(UEFA)
- link "FIFA World Cup qualification (AFC)":
  - /url: /league/FIFA%20World%20Cup%20qualification%20(AFC)
- link "FIFA World Cup qualification (CONMEBOL)":
  - /url: /league/FIFA%20World%20Cup%20qualification%20(CONMEBOL)
- link "FIFA World Cup qualification (CONCACAF)":
  - /url: /league/FIFA%20World%20Cup%20qualification%20(CONCACAF)
- link "FIFA World Cup qualification (CAF)":
  - /url: /league/FIFA%20World%20Cup%20qualification%20(CAF)
- link "FIFA Club World Cup":
  - /url: /league/FIFA%20Club%20World%20Cup
- link "UEFA European Championship":
  - /url: /league/UEFA%20European%20Championship
- link "CONMEBOL Copa America":
  - /url: /league/CONMEBOL%20Copa%20America
- link "AFC Asian Cup":
  - /url: /r/league/AFC%20Asian%20Cup
- link "CONCACAF Gold Cup":
  - /url: /league/CONCACAF%20Gold%20Cup
- link "CONMEBOL Copa Sudamericana":
  - /url: /league/CONMEBOL%20Copa%20Sudamericana
- link "Netherlands Eerste Divisie":
  - /url: /league/Netherlands%20Eerste%20Divisie
- link "English Football League Championship":
  - /url: /r/league/English%20Football%20League%20Championship
- link "Norwegian Eliteserien":
  - /url: /r/league/Norwegian%20Eliteserien
- link "Danish Superliga":
  - /url: /r/league/Danish%20Superliga
- link "Finnish Ykkosliiga":
  - /url: /league/Finnish%20Ykkosliiga
- link "Sweden Allsvenskan":
  - /url: /r/league/Sweden%20Allsvenskan
- link "Switzerland Super League":
  - /url: /r/league/Switzerland%20Super%20League
- link "Netherlands Eredivisie":
  - /url: /league/Netherlands%20Eredivisie
- link "Spanish Segunda Division":
  - /url: /league/Spanish%20Segunda%20Division
- link "Italian Serie B":
  - /url: /r/league/Italian%20Serie%20B
- link "German Bundesliga 2":
  - /url: /r/league/German%20Bundesliga%202
- link "French Ligue 2":
  - /url: /r/league/French%20Ligue%202
- link "Brazilian Campeonato Carioca A":
  - /url: /league/Brazilian%20Campeonato%20Carioca%20A
- link "Mexico Liga MX":
  - /url: /r/league/Mexico%20Liga%20MX
- link "CHI Liga de Primera":
  - /url: /league/CHI%20Liga%20de%20Primera
- link "Superliga de Colombia":
  - /url: /league/Superliga%20de%20Colombia
- link "Uruguay Primera Division":
  - /url: /league/Uruguay%20Primera%20Division
- link "Peruvian Liga 1":
  - /url: /league/Peruvian%20Liga%201
- link "Paraguayan Primera Division":
  - /url: /league/Paraguayan%20Primera%20Division
- link "Indian Calcutta Football League":
  - /url: /league/Indian%20Calcutta%20Football%20League
- link "Japanese J1 League":
  - /url: /league/Japanese%20J1%20League
- link "Korean K League 1":
  - /url: /league/Korean%20K%20League%201
- link "Australia A-League":
  - /url: /league/Australia%20A-League
- link "United Arab Emirates Adnoc Pro-League":
  - /url: /league/United%20Arab%20Emirates%20Adnoc%20Pro-League
- link "Qatar Stars League":
  - /url: /league/Qatar%20Stars%20League
- link "FA Cup":
  - /url: /league/FA%20Cup
- link "English Football League Cup":
  - /url: /league/English%20Football%20League%20Cup
- link "Copa del Rey":
  - /url: /league/Copa%20del%20Rey
- link "DFB Pokal":
  - /url: /league/DFB%20Pokal
- link "Coppa Italia":
  - /url: /league/Coppa%20Italia
- link "Coupe de France":
  - /url: /league/Coupe%20de%20France
- link "Netherlands KNVB Cup":
  - /url: /league/Netherlands%20KNVB%20Cup
- link "Copa Argentina":
  - /url: /league/Copa%20Argentina
- link "Belgian Cup":
  - /url: /league/Belgian%20Cup
- button "Show more arrow":
  - text: Show more
  - img "arrow"
- text: Hot Team
- link "Liverpool":
  - /url: /team/Liverpool/gpxwrxlhw8gryk0
- link "FC Barcelona":
  - /url: /team/FC%20Barcelona/e4wyrn4h127q86p
- link "Real Madrid":
  - /url: /team/Real%20Madrid/e4wyrn4h111q86p
- link "Paris Saint Germain":
  - /url: /team/Paris%20Saint%20Germain/kjw2r09hv44rz84
- link "Manchester United":
  - /url: /team/Manchester%20United/l965mkyh98gr1ge
- link "Arsenal":
  - /url: /team/Arsenal/z318q66hdd1qo9j
- link "Bayer 04 Leverkusen":
  - /url: /team/Bayer%2004%20Leverkusen/4zp5rzghewnq82w
- link "Juventus":
  - /url: /team/Juventus/e4wyrn4hn4dq86p
- link "AC Milan":
  - /url: /team/AC%20Milan/yl5ergph63er8k0
- link "Argentina":
  - /url: /team/Argentina/kdj2ryoh868q1zp
- link "Germany":
  - /url: /team/Germany/d23xmvkh590qg8n
- link "Indonesia":
  - /url: /team/Indonesia/jednm9whywwryox
- link "Qatar":
  - /url: /team/Qatar/d23xmvkh1y9qg8n
- link "Brazil":
  - /url: /team/Brazil/9vjxm8gh68er6od
- link "Denmark":
  - /url: /team/Denmark/8y39mp1hnlgmojx
- link "Norway":
  - /url: /team/Norway/8y39mp1h77lmojx
- link "Italy":
  - /url: /team/Italy/56ypq3nh290md7o
- link "FC Porto":
  - /url: /team/FC%20Porto/gpxwrxlhwl4ryk0
- link "FC Bayern Munich":
  - /url: /team/FC%20Bayern%20Munich/yl5ergphjy2r8k0
- link "Benfica":
  - /url: /team/Benfica/z8yomo4hjyoq0j6
- link "Tottenham Hotspur":
  - /url: /team/Tottenham%20Hotspur/l965mkyh90gr1ge
- link "Al Hilal":
  - /url: /team/Al%20Hilal/kdj2ryohw6wq1zp
- link "Newcastle United":
  - /url: /team/Newcastle%20United/8y39mp1h8dpmojx
- link "Al Nassr":
  - /url: /team/Al%20Nassr/318q66hoklkqo9j
- link "Napoli":
  - /url: /team/Napoli/4zp5rzghvdoq82w
- link "Aston Villa":
  - /url: /team/Aston%20Villa/j1l4rjnh06om7vx
- link "Atletico Madrid":
  - /url: /team/Atletico%20Madrid/9vjxm8ghodjr6od
- link "England":
  - /url: /team/England/z8yomo4hl08q0j6
- link "Inter Miami CF":
  - /url: /team/Inter%20Miami%20CF/vjxm8ghjyd1r6od
- link "Manchester City":
  - /url: /team/Manchester%20City/p4jwq2ghd57m0ve
- link "Inter Milan":
  - /url: /team/Inter%20Milan/9dn1m1ghzl2moep
- link "Chelsea":
  - /url: /team/Chelsea/j1l4rjnhpdxm7vx
- link "RB Leipzig":
  - /url: /team/RB%20Leipzig/z318q66hdleqo9j
- link "AS Roma":
  - /url: /team/AS%20Roma/gx7lm7phel7m2wd
- link "Nigeria":
  - /url: /team/Nigeria/v2y8m4zhlo0ql07
- link "Spain":
  - /url: /team/Spain/dn1m1gh4vgymoep
- link "Borussia Dortmund":
  - /url: /team/Borussia%20Dortmund/4zp5rzghe4nq82w
- link "Japan":
  - /url: /team/Japan/318q66hooj2qo9j
- link "Real Betis":
  - /url: /team/Real%20Betis/d23xmvkhz9nqg8n
- link "Porto SC":
  - /url: /team/Porto%20SC/3glrw7hwwj8qdyj
- link "France":
  - /url: /team/France/p4jwq2ghdj9m0ve
- link "Sporting CP":
  - /url: /team/Sporting%20CP/kn54qllhyydqvy9
- link "Portugal":
  - /url: /team/Portugal/z8yomo4hwpeq0j6
- link "FC Los Angeles":
  - /url: /team/FC%20Los%20Angeles/vjxm8ghpkezr6od
- link "AS Monaco":
  - /url: /team/AS%20Monaco/yl5ergph6ner8k0
- link "Netherlands":
  - /url: /team/Netherlands/9dn1m1ghzj5moep
- link "Belgium":
  - /url: /team/Belgium/z318q66hd5eqo9j
- link "Lyon":
  - /url: /team/Lyon/8y39mp1hg8lmojx
- link "Fenerbahce":
  - /url: /team/Fenerbahce/56ypq3nhdpymd7o
- link "Marseille":
  - /url: /team/Marseille/kjw2r09hyl1rz84
- link "Villarreal CF":
  - /url: /team/Villarreal%20CF/kjw2r09hvwwrz84
- link "AFC Ajax":
  - /url: /team/AFC%20Ajax/jednm9whl7kryox
- link "Galatasaray":
  - /url: /team/Galatasaray/z318q66hp66qo9j
- link "FK Bodo/Glimt":
  - /url: /team/FK%20Bodo%2FGlimt/l965mkyh9xyr1ge
- link "Celtic F.C.":
  - /url: /team/Celtic%20F.C./9vjxm8gho3or6od
- link "Rangers F.C.":
  - /url: /team/Rangers%20F.C./kdj2ryoh0ydq1zp
- link "Union Saint-Gilloise":
  - /url: /team/Union%20Saint-Gilloise/pxwrxlhg1lxryk0
- link "Anderlecht":
  - /url: /team/Anderlecht/kdj2ryoh3ozq1zp
- link "Royal Antwerp":
  - /url: /team/Royal%20Antwerp/l5ergphoe4lr8k0
- link "KAA Gent":
  - /url: /team/KAA%20Gent/l965mkyh99yr1ge
- link "Club Brugge":
  - /url: /team/Club%20Brugge/9vjxm8ghowor6od
- link "Racing Genk":
  - /url: /team/Racing%20Genk/9dn1m1ghdzgmoep
- link "Standard Liege":
  - /url: /team/Standard%20Liege/e4wyrn4h1n1q86p
- link "Morocco":
  - /url: /team/Morocco/56ypq3nh9nzmd7o
- link "Senegal":
  - /url: /team/Senegal/p4jwq2ghlx3m0ve
- link "Nottingham Forest":
  - /url: /team/Nottingham%20Forest/v2y8m4zhdx6ql07
- link "Crystal Palace":
  - /url: /team/Crystal%20Palace/vl7oqdehzkpr510
- link "Everton":
  - /url: /team/Everton/p3glrw7he21qdyj
- link "Sunderland":
  - /url: /team/Sunderland/p3glrw7he6gqdyj
- link "Brighton&Hove Albion":
  - /url: /team/Brighton%20Hove%20Albion/9k82rekhd6orepz
- link "Como":
  - /url: /team/Como/z8yomo4hnz4q0j6
- link "Midtjylland":
  - /url: /team/Midtjylland/gy0or5jhdvoqwzv
- link "Torino":
  - /url: /team/Torino/z8yomo4hw6lq0j6
- link "South Korea":
  - /url: /team/South%20Korea/jednm9wh4x9ryox
- link "USA":
  - /url: /team/USA/kn54qllhv3xqvy9
- link "Turkiye":
  - /url: /team/Turkiye/kn54qllhvxyqvy9
- link "Uruguay":
  - /url: /team/Uruguay/z318q66hln7qo9j
- link "Colombia":
  - /url: /team/Colombia/p3glrw7h5y7qdyj
- link "Palmeiras - SP":
  - /url: /team/Palmeiras%20-%20SP/4zp5rzgh993q82w
- link "Flamengo - RJ":
  - /url: /team/Flamengo%20-%20RJ/yl5ergphj44r8k0
- link "Santos Fc - SP":
  - /url: /team/Santos%20Fc%20-%20SP/l965mkyhvd7r1ge
- link "Fluminense - RJ":
  - /url: /team/Fluminense%20-%20RJ/p3glrw7he4vqdyj
- link "Corinthians - SP":
  - /url: /team/Corinthians%20-%20SP/v2y8m4zh9znql07
- link "Cruzeiro - MG":
  - /url: /team/Cruzeiro%20-%20MG/4zp5rzghee0q82w
- link "River Plate":
  - /url: /team/River%20Plate/56ypq3nhop0md7o
- link "Estudiantes La Plata":
  - /url: /team/Estudiantes%20La%20Plata/gx7lm7pheg8m2wd
- link "Boca Juniors":
  - /url: /team/Boca%20Juniors/z8yomo4hj31q0j6
- link "CA Rosario Central":
  - /url: /team/CA%20Rosario%20Central/z8yomo4hoxyq0j6
- link "Coventry City":
  - /url: /team/Coventry%20City/kdj2ryoh30zq1zp
- link "Ipswich Town":
  - /url: /team/Ipswich%20Town/j1l4rjnhpo5m7vx
- link "Hull City":
  - /url: /team/Hull%20City/jednm9wh4d9ryox
- button "Show more arrow":
  - text: Show more
  - img "arrow"
- text: Hot Players
- link "Rodrigo Hernandez Cascante":
  - /url: /player/Rodrigo%20Hernandez%20Cascante/4wyrn4hvlloq86p
- link "Aurelien Tchouameni":
  - /url: /player/Aurelien%20Tchouameni/pxwrxlhv2peryk0
- link "Nuno Mendes":
  - /url: /player/Nuno%20Mendes/l5ergphvlzwor8k
- link "Martin Odegaard":
  - /url: /player/Martin%20Odegaard/4wyrn4hdjonq86p
- link "Bryan Mbeumo":
  - /url: /player/Bryan%20Mbeumo/y0or5jh4d2yjqwz
- link "Raphael Dias Belloli":
  - /url: /player/Raphael%20Dias%20Belloli/23xmvkh48j7qg8n
- link "Phil Foden":
  - /url: /player/Phil%20Foden/ednm9whedo0ryox
- link "Alessandro Bastoni":
  - /url: /player/Alessandro%20Bastoni/n54qllhj1zvqvy9
- link "Pau Cubarsí":
  - /url: /player/Pau%20Cubars%C3%AD/23xmvkhk1e18qg8
- link "Estêvão Willian Almeida de Oliveira Gonçalves":
  - /url: /player/Est%C3%AAv%C3%A3o%20Willian%20Almeida%20de%20Oliveira%20Gon%C3%A7alves/ednm9whgg9x7ryo
- link "Achraf Hakimi":
  - /url: /player/Achraf%20Hakimi/dj2ryohnk9nq1zp
- link "Hugo Ekitiké":
  - /url: /player/Hugo%20Ekitik%C3%A9/y0or5jhev00eqwz
- link "Lautaro Martínez":
  - /url: /player/Lautaro%20Mart%C3%ADnez/4wyrn4hv7ydq86p
- link "Alexis Mac Allister":
  - /url: /player/Alexis%20Mac%20Allister/1l4rjnh3p29m7vx
- link "Enzo Fernández":
  - /url: /player/Enzo%20Fern%C3%A1ndez/l7oqdeh4dx80r51
- link "Dominik Szoboszlai":
  - /url: /player/Dominik%20Szoboszlai/3glrw7ho7x7qdyj
- link "Khvicha Kvaratskhelia":
  - /url: /player/Khvicha%20Kvaratskhelia/l7oqdehe9j7r510
- link "Ryan Gravenberch":
  - /url: /player/Ryan%20Gravenberch/n54qllheyly3qvy
- link "William Saliba":
  - /url: /player/William%20Saliba/pxwrxlh9e758ryk
- link "Arda Güler":
  - /url: /player/Arda%20G%C3%BCler/3glrw7hyo0kdqdy
- link "Désiré Doue":
  - /url: /player/D%C3%A9sir%C3%A9%20Doue/vjxm8gh85pnpr6o
- link "Ousmane Dembélé":
  - /url: /player/Ousmane%20Demb%C3%A9l%C3%A9/318q66hjv6kqo9j
- link "Julián Álvarez":
  - /url: /player/Juli%C3%A1n%20%C3%81lvarez/318q66hvngwvqo9
- link "Vitinha":
  - /url: /player/Vitinha/l5ergphv839er8k
- link "João Neves":
  - /url: /player/Jo%C3%A3o%20Neves/1l4rjnhxj6gem7v
- link "Florian Wirtz":
  - /url: /player/Florian%20Wirtz/1l4rjnhzgol1m7v
- link "Moises Caicedo":
  - /url: /player/Moises%20Caicedo/965mkyh3204gr1g
- link "Cole Palmer":
  - /url: /player/Cole%20Palmer/1l4rjnhzl44em7v
- link "Federico Valverde":
  - /url: /player/Federico%20Valverde/dj2ryohnl5gq1zp
- link "Alexander Isak":
  - /url: /player/Alexander%20Isak/l7oqdehleg1r510
- link "Declan Rice":
  - /url: /player/Declan%20Rice/ednm9whev1dryox
- link "Michael Olise":
  - /url: /player/Michael%20Olise/y0or5jhe6zx2qwz
- link "Bukayo Saka":
  - /url: /player/Bukayo%20Saka/x7lm7ph0854om2w
- link "Jamal Musiala":
  - /url: /player/Jamal%20Musiala/3glrw7hj7vjoqdy
- link "Pedri":
  - /url: /player/Pedri/318q66hvwjy3qo9
- link "Vinícius":
  - /url: /player/Vin%C3%ADcius/1l4rjnhe42vm7vx
- link "Jude Bellingham":
  - /url: /player/Jude%20Bellingham/3glrw7hj71ldqdy
- link "Lamine Yamal":
  - /url: /player/Lamine%20Yamal/4jwq2ghxjzkvm0v
- link "Cristiano Ronaldo":
  - /url: /player/Cristiano%20Ronaldo/j1l4rjnhpgxm7vx
- link "Kylian Mbappé":
  - /url: /player/Kylian%20Mbapp%C3%A9/pxwrxlhze0dryk0
- link "Lionel Messi":
  - /url: /player/Lionel%20Messi/p3glrw7hv73qdyj
- link "Erling Haaland":
  - /url: /player/Erling%20Haaland/2y8m4zhzd27ql07
- button "Show more arrow":
  - text: Show more
  - img "arrow"
- text: Visit localized version of Camel Live
- link "Camel Live English":
  - /url: /en
- link "Camel Live العربية":
  - /url: /ar
- link "Camel Live हिंदी":
  - /url: /hi
- link "Camel Live বাংলা":
  - /url: /bn
- link "Camel Live Indonesia":
  - /url: /id
- link "Camel Live Español":
  - /url: /es
- link "Camel Live Português (Brasil)":
  - /url: /pt-BR
- link "Camel Live Português (Portugal)":
  - /url: /pt-PT
- link "Camel Live Winter Transfer Special Page":
  - /url: /winter-window
- link "Free Football Live Streaming — Watch Football Online Free":
  - /url: /free-football-live-streaming
- link "Telegram":
  - /url: https://tinyurl.com/srf52pur
  - img "Telegram"
- link "Instagram":
  - /url: "https://www.instagram.com/camel_sports0?igsh=MXh5ZDJvcGE3ZWg5cA%3D%3D&utm_source=qr\n"
  - img "Instagram"
- link "YouTube":
  - /url: https://youtube.com/@camelsport?si=rlqIIppcIl4OA4NG
  - img "YouTube"
- link "TikTok":
  - /url: https://www.tiktok.com/@sportega1?_t=ZS-8xEyPPxiweA&_r=1
  - img "TikTok"
- link "Facebook":
  - /url: https://www.facebook.com/share/1DtoNZcYX8/?mibextid=wwXIfr
  - img "Facebook"
- link "Subscribe to RSS Feed":
  - /url: /rss.xml
- link "About Us":
  - /url: /about-us
- text: "|"
- link "Contact Us":
  - /url: /contact-us
- text: "|"
- link "Terms And Policy":
  - /url: /terms
- text: "|"
- link "Feedback":
  - /url: /my/feedback
- text: Copyright @ 2026 Camel Live
```

# Test source

```ts
  1   | import { expect, test, type Page } from '@playwright/test'
  2   | 
  3   | import {
  4   |   assertP0RequestAllowed,
  5   |   readP0Runtime,
  6   |   type P0Runtime,
  7   | } from '../support/production-p0-contract'
  8   | 
  9   | const API_URL_PATTERN = /api\./i
  10  | 
  11  | async function guardP0(page: Page, runtime: P0Runtime): Promise<string[]> {
  12  |   const rejected: string[] = []
  13  |   await page.route('**/*', async (route) => {
  14  |     const request = route.request()
  15  |     try {
  16  |       assertP0RequestAllowed(runtime, request.url(), request.method())
  17  |       await route.continue()
  18  |       return
  19  |     } catch (error) {
  20  |       rejected.push(error instanceof Error ? error.message : String(error))
  21  |       await route.abort('blockedbyclient')
  22  |     }
  23  |   })
  24  |   return rejected
  25  | }
  26  | 
  27  | function apiObservations(page: Page): string[] {
  28  |   const urls: string[] = []
  29  |   page.on('response', (response) => {
  30  |     if (API_URL_PATTERN.test(response.url())) {
  31  |       urls.push(response.url())
  32  |     }
  33  |   })
  34  |   return urls
  35  | }
  36  | 
  37  | test.describe('体育平台 生产 P0 功能用例 → UI 自动化（只读）', () => {
  38  |   let runtime: P0Runtime
  39  | 
  40  |   test.beforeAll(() => {
  41  |     runtime = readP0Runtime()
  42  |   })
  43  | 
  44  |   test.beforeEach(async ({ page }) => {
  45  |     page.setDefaultTimeout(20_000)
  46  |     page.setDefaultNavigationTimeout(30_000)
  47  |   })
  48  | 
  49  |   test.afterEach(async ({ page }, testInfo) => {
  50  |     const dir = process.env.P0_EVIDENCE_DIR || 'p0-evidence'
  51  |     await page
  52  |       .screenshot({
  53  |         path: `${dir}/${testInfo.title.replace(/[^\w\u4e00-\u9fa5-]/g, '_').slice(0, 80)}.png`,
  54  |         fullPage: false,
  55  |       })
  56  |       .catch(() => undefined)
  57  |   })
  58  | 
  59  |   test('P0-UI-001 首页：Live Matches/搜索/REGISTER + 核心 API 资产', async ({ page }) => {
  60  |     const rejected = await guardP0(page, runtime)
  61  |     const apiUrls = apiObservations(page)
  62  |     const response = await page.goto(runtime.baseUrl.toString(), { waitUntil: 'networkidle' })
  63  |     expect(response?.status() ?? 0).toBeGreaterThanOrEqual(200)
  64  |     await expect(page.getByText(/Live Matches|Favorites|Competitions/i).first()).toBeVisible()
  65  |     await expect(page.locator('input[type="text"], input[type="search"]').first()).toBeVisible()
> 66  |     await expect(page.getByText(/REGISTER|Register/i).first()).toBeVisible()
      |                                                                ^ Error: expect(locator).toBeVisible() failed
  67  |     expect(apiUrls.some((u) => /ads\/activity|search\/hot|client\/general/i.test(u))).toBe(true)
  68  |     expect(rejected).toEqual([])
  69  |   })
  70  | 
  71  |   test('P0-UI-002 赛事详情：标题/比分/标签渲染', async ({ page }) => {
  72  |     const rejected = await guardP0(page, runtime)
  73  |     await page.goto(new URL('/football/as-monaco-vs-getafe/n54qllhn0vwjqvy', runtime.baseUrl).toString(), {
  74  |       waitUntil: 'domcontentloaded',
  75  |     })
  76  |     await expect(page.getByText(/AS Monaco|Getafe|Monaco/i).first()).toBeVisible()
  77  |     const headings = await page.locator('h1,h2,h3').allTextContents()
  78  |     expect(headings.join(' ').length).toBeGreaterThan(10)
  79  |     expect(rejected).toEqual([])
  80  |   })
  81  | 
  82  |   test('P0-UI-003 直播间：视频容器/直播页面渲染', async ({ page }) => {
  83  |     const rejected = await guardP0(page, runtime)
  84  |     await page.goto(new URL('/football/persatuan-sepakbola-indonesia-jakarta-vs-arema-fc/live/2y8m4zh5kwgpql0', runtime.baseUrl).toString(), {
  85  |       waitUntil: 'domcontentloaded',
  86  |     })
  87  |     await expect(page.locator('[class*="roomLive"]').first()).toBeVisible()
  88  |     await expect(page.getByText(/Live Streaming|Live Score/i).first()).toBeVisible()
  89  |     expect(rejected).toEqual([])
  90  |   })
  91  | 
  92  |   test('P0-UI-004 资讯：列表 + 首条资讯详情可达', async ({ page }) => {
  93  |     const rejected = await guardP0(page, runtime)
  94  |     await page.goto(new URL('/q/news', runtime.baseUrl).toString(), { waitUntil: 'networkidle' })
  95  |     const articleLinks = page.locator('a[href*="/news/detail/"]')
  96  |     await expect(articleLinks.first()).toBeVisible()
  97  |     const href = await articleLinks.first().getAttribute('href')
  98  |     expect(href).toBeTruthy()
  99  |     expect(rejected).toEqual([])
  100 |   })
  101 | 
  102 |   test('P0-UI-005 搜索：输入查询并看到结果（查询型 POST 放行）', async ({ page }) => {
  103 |     const rejected = await guardP0(page, runtime)
  104 |     await page.goto(new URL('/search', runtime.baseUrl).toString(), { waitUntil: 'domcontentloaded' })
  105 |     const input = page.locator('input[type="text"], input[type="search"]').first()
  106 |     await expect(input).toBeVisible()
  107 |     await input.fill('Real Madrid')
  108 |     await page.keyboard.press('Enter')
  109 |     await page.waitForTimeout(2500)
  110 |     const bodyText = await page.locator('body').innerText()
  111 |     expect(/Real Madrid|real madrid/i.test(bodyText)).toBe(true)
  112 |     expect(rejected).toEqual([])
  113 |   })
  114 | 
  115 |   test('P0-UI-006 我的：Login 引导 + 资产/功能入口渲染', async ({ page }) => {
  116 |     const rejected = await guardP0(page, runtime)
  117 |     await page.goto(new URL('/my', runtime.baseUrl).toString(), { waitUntil: 'domcontentloaded' })
  118 |     await expect(page.getByText(/Login|登录/i).first()).toBeVisible()
  119 |     await expect(page.getByText(/Silver Diamond|Camel Mall|Favorites|Outfits|FAQ/i).first()).toBeVisible()
  120 |     expect(rejected).toEqual([])
  121 |   })
  122 | 
  123 |   test('P0-UI-007 联赛：积分榜/赛程表面渲染', async ({ page }) => {
  124 |     const rejected = await guardP0(page, runtime)
  125 |     await page.goto(new URL('/r/league/UEFA%20Europa%20League', runtime.baseUrl).toString(), { waitUntil: 'domcontentloaded' })
  126 |     await expect(page.getByText(/UEFA Europa League/i).first()).toBeVisible()
  127 |     const bodyText = await page.locator('body').innerText()
  128 |     expect(/Standings|Schedule|Fixture/i.test(bodyText)).toBe(true)
  129 |     expect(rejected).toEqual([])
  130 |   })
  131 | 
  132 |   test('P0-UI-008 回放：列表渲染记录', async ({ page }) => {
  133 |     const rejected = await guardP0(page, runtime)
  134 |     await page.goto(new URL('/match-replay', runtime.baseUrl).toString(), { waitUntil: 'networkidle' })
  135 |     const replayLinks = page.locator('a[href*="/match-replay/"]')
  136 |     await expect(replayLinks.first()).toBeVisible()
  137 |     expect(rejected).toEqual([])
  138 |   })
  139 | 
  140 |   test('P0-UI-009 世界杯：Match Center/Schedule/Groups/Bracket 表面', async ({ page }) => {
  141 |     const rejected = await guardP0(page, runtime)
  142 |     await page.goto(new URL('/worldcup-2026', runtime.baseUrl).toString(), { waitUntil: 'domcontentloaded' })
  143 |     await expect(page.getByText(/World Cup 2026|FIFA World Cup/i).first()).toBeVisible()
  144 |     const bodyText = await page.locator('body').innerText()
  145 |     expect(/Match Center|Schedule|Groups|Bracket/i.test(bodyText)).toBe(true)
  146 |     expect(rejected).toEqual([])
  147 |   })
  148 | 
  149 |   test('P0-UI-010 首页加载性能：15s 内完成', async ({ page }) => {
  150 |     const rejected = await guardP0(page, runtime)
  151 |     const startedAt = Date.now()
  152 |     await page.goto(runtime.baseUrl.toString(), { waitUntil: 'load' })
  153 |     expect(Date.now() - startedAt).toBeLessThan(15_000)
  154 |     expect(rejected).toEqual([])
  155 |   })
  156 | })
  157 | 
```