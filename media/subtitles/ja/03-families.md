# Episode 3 subtitles: Japanese

Japanese subtitles for `media/episodes/03-families.md`. Each `##` heading is a scene number in that script, and each line under it is one subtitle cue; a line in ［brackets］ translates on-screen text. Numbers are tokens, filled from the dataset like the script's. The build times the cues across each scene's narration at 135 words a minute and writes `dist/media/subtitles/ja/03-families.srt`; retime against the recorded voice before release.

## 1

Factorioでは、電力が足りないと
送電網のすべての機械が同じ割合で遅くなります。
そして炉から出る煙が、
これからあなたを襲う巣を育てています。
Anno 1800では、職人の家が並ぶ通りが
別の島から届く缶詰のグーラッシュを待っています。
それを積んだ船は遅れています。
どちらのゲームも生産チェーンで動いています。
データセットは、2つを別のファミリーに入れています。

## 2

［ジャンルをまたぐファミリー　第3話］

## 3

FactorioとAnno 1800が共有するメカニクスは6つ。
最も一般的な2つは、生産チェーンが{{derived:production-chain.prevalence}}本、
建物の配置が{{derived:free-placement.prevalence}}本のゲームにあります。
それぞれにしかない部品のほうが珍しく、
ゲームの手ざわりを決めています。
Factorioはスループットのゲームです。
ベルト、電力、汚染、そして
あなたの出す汚染とともに進化する敵。
Annoは需要のゲームです。
5段階の住民の欲求が、家が格上げされるかどうかを決め、
それを満たすために島から島へ品物を運びます。
各階層は、自分の工場で働く人手でもあります。
労働者が職人に上がると、
労働者の生産チェーンは人手を失います。

## 4

ゲームをグループに分けるため、
データセットは各ゲームをメカニクスのリストに変えます。
コアの部品は2倍に数えます。
部品は珍しいほど重く扱われます。
珍しい部品を共有する2本は、
ポーズボタンを共有する2本よりずっと近いとみなされます。
生産チェーンは{{derived:production-chain.prevalence}}本にあるので軽く、
ベルトコンベアは{{derived:conveyor-transport.prevalence}}本なので重く数えます。
そのうえでビルドは、最も近いゲーム同士、
最も近いグループ同士を、決めた数のクラスタになるまでつなぎます。
Factorioの隣には、Satisfactory、shapez 2、
Dyson Sphere Program、Captain of Industry。
Anno 1800の隣には、Manor Lords、Banished、
Caesar III、Pharaohが来ます。

## 5

ビルドは、ゲームのランダムな部分集合{{stat:cluster_subsamples}}個でクラスタリングをやり直し、
それぞれが全体の結果とどれだけ一致するかを確かめます。
決めたルールでは、平均の一致度が{{stat:cluster_min_mean_ari}}に届く
最小のクラスタ数を選びます。
前回それを適用したときは{{stat:cluster_k}}でした。
今日のデータでは、同じルールが{{stat:cluster_rule_k}}を選びます。
それほど曲線は平らです。
だからファミリーの数は弱い事実で、
このシリーズは再標本化に耐えた組み合わせだけを主張します。
2本が同じファミリーだと言うときは、
部分集合の{{stat:cocluster_together}}以上で同じクラスタに入っています。
離れていると言うときは、{{stat:cocluster_apart}}以下です。
どの主張も、データセットをビルドするたびに確かめられます。
別の尺度では、{{stat:n_clusters}}個のクラスタのうち
{{stat:n_stable_clusters}}個が再標本化の間も形を保ち、
残りはゲームの出入りで形を変えます。
［同じ：部分集合の{{stat:cocluster_together}}以上。別：{{stat:cocluster_apart}}以下］

## 6

Papers, Pleaseは、国境でパスポートを調べるゲームです。
1993年のプリンセスメーカー2は、
娘を10歳から18歳まで育てるゲームです。
この2本は同じファミリーです。
どちらも、時間は決まった枠でやって来て、
お金は苦しく、用意されたイベントが次々に届きます。
国境では、正しい判断ごとに給料が出て、
ミスはファックスで届く違反通知になります。
給料は、家族の家賃と食費と暖房に消えます。
国境での1回の勤務と、娘の1か月は、同じ種類の予算です。
Job SimulatorはBesiegeやThe Incredible Machineと同じ仲間です。
手の届く物のほとんどが、つかみ、投げ、
組み合わせられる物理オブジェクトだからです。
ほかの2本のジョブシム、PowerWash SimulatorとHouse Flipperは、
道具と請負仕事でできた、別のファミリーにいます。
Farming Simulatorはレースゲームと同じ側にいて、
Stardew Valleyや牧場物語とは離れています。
その農場は、400台を超える実在メーカーの機械の車両群で、
畑仕事を順番にこなします。腕前とは、それを操ることです。
Black & Whiteは神ゲームですが、
このジャンルを始めたPopulousとは離れています。
育てるクリーチャーがいるので、
仮想ペットやCreaturesと同じ側に入ります。
Tropico 6は都市建設ゲームに分類されていますが、
SimCityとは離れています。
そのファミリーは統治者たちです。
Europa Universalis IV、Civilization、Stellaris。
安定度、政策の選択、利益集団でまとまっています。
Theme Hospital、RollerCoaster Tycoon、Game Dev Tycoonは、
スタッフの雇用、研究、好みを持つ群衆でまとまります。
患者や来場者にはThe Simsの住人と同じく欲求がありますが、
それでもライフシムとは離れています。
プレイヤーが動かしているのは、群衆に仕える商売だからです。
コロニーシムはまとまっています。
RimWorldとDwarf Fortress、Oxygen Not Included。
ライフシムも同じで、The SimsとParalivesがまとまります。
2つのグループはほとんどの再標本化で同じクラスタに入りますが、
それぞれのグループ内ほど頻繁ではありません。
inZOIは、打ち込んだプロンプトで
端末上のモデルを通してキャラクターを動かせます。
でも欲求で動くコアはThe Sims型なので、
The Simsの側に入り、AI DungeonやInfinite Craftとは離れます。

## 7

シリーズはまとまります。
SimCityとSimCity 4、The SimsとThe Sims 4。
そして30年離れたEliteとElite Dangerousも、
生成された星系、交易、自分で飛ばす船でつながります。
この手法は、名前の違う子孫も見つけます。
2015年のOffworld Trading Companyは、
1983年のM.U.L.E.と、すべての再標本化で同じファミリーです。
その設計者は、M.U.L.E.とRailroad Tycoonを着想源に挙げています。
価格は売り買いのたびに動き、
ライバルの株を買い占めると勝ちです。
カタログでこのメカニクスを最初に記録しているのは、Railroad Tycoonです。
こうした古い交易ゲームは、工場ゲームとも弱くつながっています。
FactorioがRailroad Tycoonと同じクラスタに入るのは再標本化の約半分。
Satisfactoryとは、すべてで同じです。

## 8

Frostpunkは、カタログで唯一、分かれるシリーズです。
Frostpunkは、ひとつの石炭ジェネレーターを囲む
サバイバル都市建設ゲームです。
気温は予定どおりに下がり、
署名する法律は、民の暮らしと生産量を引き換えにします。
最も近い隣は、Against the Stormです。
Frostpunk 2は、建物ではなく地区を建て、
100人の代表からなる評議会で法律を通します。
ほとんどの法律には51票が必要です。
約束を破れば派閥が怒り、
派閥の対立は内戦で終わることもあります。
開発者は、寒さよりも社会の存続のほうが大きな脅威だと説明しています。
その部品はTropico 6やEuropa Universalis IVの側にあり、
1作目と同じクラスタに入るのは、再標本化の半分に満たない回数です。

## 9

ゲームのファミリーが分かれば、ジャンルもかなり分かります。
正規化相互情報量は{{stat:cluster_subgenre_nmi}}。
ラベルをランダムに入れ替えると{{stat:cluster_subgenre_null_nmi}}です。
もっと厳しい調整ランド指数では、
1ならファミリーがジャンルを完全に再現することになりますが、
一致は{{stat:cluster_subgenre_ari}}にとどまります。
そして{{stat:n_clusters}}個のクラスタのうち{{stat:n_clusters_cross_subgenre}}個は、ジャンルが混ざっています。
メカニクスは、偶然よりはるかによくゲームの出自を言い当てますが、
それでもジャンルの線をよく越えます。
ゲームのファミリーは、それが何でできているかを示します。
デザイナーが借りられるのは、その部分です。

## 10

メカニクスがとても少ないゲームは、
欠けているもので似て見えます。
ライフゲームのメカニクスは{{derived:game-of-life.mechanic_count}}個だけ。
そのひとつはHamurabiやThe Oregon Trailと共通のターン構造なので、
それらと同じクラスタに入ります。
再標本化で崩れるクラスタもあります。
Frostpunk、Plague Inc.、Timberborn、FTLを含むクラスタは
部分集合ごとに変わり、
まとまり続けるのはFrostpunkとAgainst the Stormだけです。
クラスタリングは、ゲームがどの部品を使うかは見ますが、
どう調整されているかは見ていません。
しかも、ここまでの分解はすべて
ひとつのモデル評価者が書いたものです。
2人目の評価者が、これらのファミリーの次の検証になります。

## 11

知っているゲームで、珍しい部品に丸をつけ、
2つ以上を共有するカタログのゲームを探してください。
ジャンルが何であれ、それがそのゲームのファミリーです。
次に、ストアページで一番似ていないメンバーを選び、
共有する部品をどう扱っているかを読んで、
あなたのゲームが取り入れられることをひとつ書き出します。
RimWorldとDwarf Fortressは、
すべての再標本化で同じファミリーに入り、
どちらもカタログで最も高い創発性の評価を持っています。
次回は、最も深いシステムが
なぜ最も読みにくいのかを見ていきます。
［データセット、論文、すべての出典：simgrammar.com］
