# Stage 2 트렌드 템플릿 (한국)

## Minervini 7-Point Template

| # | 조건 | 코드 |
|---|------|------|
| 1 | Close > SMA(150) AND Close > SMA(200) | `price > sma150 and price > sma200` |
| 2 | SMA(150) > SMA(200) | `sma150 > sma200` |
| 3 | SMA(200) 22일+ 상승 | `sma200_today > sma200_22d_ago` |
| 4 | Close > SMA(50) | `price > sma50` |
| 5 | Close ≥ 52W Low × 1.25 | `price >= low_52w * 1.25` |
| 6 | Close ≥ 52W High × 0.75 | `price >= high_52w * 0.75` |
| 7 | RS Rank > 70 | `rs_rank > 70` |

## Stage 분류
- **Stage 1** (Accumulation): 200 SMA 횡보, 거래량 서서히 증가
- **Stage 2** (Advancing): 200 SMA 상승, 7점 템플릿 6점+ 통과
- **Stage 3** (Distribution): 200 SMA 평탄화, 거래량 불안정
- **Stage 4** (Declining): 200 SMA 하락, 모멘텀 이탈
