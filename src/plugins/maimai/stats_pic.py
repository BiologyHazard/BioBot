from bisect import bisect_right
from typing import Any

import pyecharts.options as opts
from PIL import Image
from pyecharts.charts import Pie
from pyecharts.render import make_snapshot
from snapshot_phantomjs import snapshot

from .config import plugin_config
from .consts import DIFFICULTY_NAME, COMBO_RANK, SCORE_RANK
from .music import Chart, ChartStats, LevelStats, Mai, Music


# def music_global_data(music: Music, diff_index: int) -> Image.Image:
#     stats: ChartStats = music.charts[diff_index].stats
#     fc_data_pair: list[list[str | int]] = [list(z) for z in zip([c.upper() if c else 'Not FC' for c in [''] + comboRank], stats.fc_dist)]
#     acc_data_pair: list[list[str | int]] = [list(z) for z in zip([s.upper() for s in scoreRank], stats.dist)]

#     Pie(
#         init_opts=opts.InitOpts(
#             width='1000px',
#             height='800px',
#             bg_color='#fff',
#             # js_host='./'
#         )
#     ).add(
#         series_name='全连等级',
#         data_pair=fc_data_pair,
#         radius=[0, '30%'],
#         label_opts=opts.LabelOpts(
#             position='outside',
#             formatter='{a|{a}}{abg|}\n{hr|}\n {b|{b}: }{c}  {per|{d}%}  ',
#             background_color='#eee',
#             border_color='#aaa',
#             border_width=1,
#             border_radius=4,
#             rich={
#                 'a': {'color': '#999', 'lineHeight': 22, 'align': 'center'},
#                 'abg': {
#                     'backgroundColor': '#e3e3e3',
#                     'width': '100%',
#                     'align': 'right',
#                     'height': 22,
#                     'borderRadius': [4, 4, 0, 0],
#                 },
#                 'hr': {
#                     'borderColor': '#aaa',
#                     'width': '100%',
#                     'borderWidth': 0.5,
#                     'height': 0,
#                 },
#                 'b': {'fontSize': 16, 'lineHeight': 33},
#                 'per': {
#                     'color': '#eee',
#                     'backgroundColor': '#334455',
#                     'padding': [2, 4],
#                     'borderRadius': 2,
#                 },
#             },
#         )
#     ).add(
#         series_name='达成率等级',
#         data_pair=acc_data_pair,
#         radius=['50%', '70%'],
#         is_clockwise=True,
#         label_opts=opts.LabelOpts(
#             position='outside',
#             formatter='{a|{a}}{abg|}\n{hr|}\n {b|{b}: }{c}  {per|{d}%}  ',
#             background_color='#eee',
#             border_color='#aaa',
#             border_width=1,
#             border_radius=4,
#             rich={
#                 'a': {'color': '#999', 'lineHeight': 22, 'align': 'center'},
#                 'abg': {
#                     'backgroundColor': '#e3e3e3',
#                     'width': '100%',
#                     'align': 'right',
#                     'height': 22,
#                     'borderRadius': [4, 4, 0, 0],
#                 },
#                 'hr': {
#                     'borderColor': '#aaa',
#                     'width': '100%',
#                     'borderWidth': 0.5,
#                     'height': 0,
#                 },
#                 'b': {'fontSize': 16, 'lineHeight': 33},
#                 'per': {
#                     'color': '#eee',
#                     'backgroundColor': '#334455',
#                     'padding': [2, 4],
#                     'borderRadius': 2,
#                 },
#             },
#         )
#     ).set_global_opts(
#         title_opts=opts.TitleOpts(
#             title=f'{music.id} {music.title} {DIFFICULTY_NAME[diff_index]}',
#             pos_left='center',
#             pos_top='20',
#             title_textstyle_opts=opts.TextStyleOpts(color='#2c343c', font_family='Microsoft Yahei'),
#         ),
#         legend_opts=opts.LegendOpts(
#             pos_left=15,
#             pos_top=10,
#             orient='vertical'
#         )
#     ).set_series_opts(
#         tooltip_opts=opts.TooltipOpts(
#             trigger='item', formatter='{a} <br/>{b}: {c} ({d}%)'
#         )
#     ).render(str(plugin_config.data_path / 'temp_pie.html'))

#     make_snapshot(snapshot,
#                   str(plugin_config.data_path / 'temp_pie.html'),
#                   str(plugin_config.data_path / 'temp_pie.png'),
#                   is_remove_html=False)

#     image: Image.Image = Image.open(plugin_config.data_path / 'temp_pie.png')
#     return image


def get_std_dev_text(std_dev: float) -> str:
    '''
    极高 4.80..
    高 4.20..4.80
    较高 3.60..4.20
    正常 0.00..3.60
    '''
    return ['正常', '较高', '高', '极高'][bisect_right([3.60, 4.20, 4.80], std_dev)]


def chart_stats_text(music: Music, diff_index: int) -> str:
    '''
    834. PANDORA PARADOXXX | Re:MASTER 15.0
    斜杠后为合计值，小括号内为同等级平均值，中括号内为二者之差
    【基础信息】
    · 游玩次数：　　  11864
    · 定数：　　　　  15.0
    · 拟合定数：　　  15.25
    · 平均达成率：　  82.1903% [+0.00%]
    · 达成率标准差：  极高 5.0045% [+0.00%]
    · 平均DX分数　　：2350.78
    · 平均DX分数比例：58.39% [+0.00%]
    · SSS占比：　　  1.50% [+0.00%]
    · SSS+占比：　　 0.59% [+0.00%]
    · FC占比：　　　　1.30% [+0.00%]
    · AP占比：　　　　0.08% [+0.00%]

    【达成率分布】
    · SSS+ 0.59% / 0.59% (0.59% / 0.59%) [+0.00% / +0.00%]
    ...
    【全连分布】
    · AP+ 0.05% / 0.05% (0.05% / 0.05%) [+0.00% / +0.00%]
    ...
    '''

    chart: Chart = music.charts[diff_index]
    stats: ChartStats = chart.stats
    level_stats: LevelStats = Mai.diff_data[music.level[diff_index]]
    score_rank_data: list[tuple[str, float, float, float, float]] = []
    '''`[('SSS+', 0.59%, 0.59%, 0.59%, 0.59%), ...]`'''
    combo_rank_data: list[tuple[str, float, float, float, float]] = []
    '''`[('AP+', 0.05%, 0.05%, 0.05%, 0.05%), ...]`'''
    for i, score_rank in enumerate(SCORE_RANK):
        score_rank_data.append((
            score_rank,
            stats.dist[i] / stats.count,
            sum(stats.dist[i:]) / stats.count,
            level_stats.dist[i],
            sum(level_stats.dist[i:]),
            # stats.dist[i] / stats.count - level_stats.dist[i],
            # sum(stats.dist[i:]) / stats.count - sum(level_stats.dist[i:]),
        ))
    for i, combo_rank in enumerate(COMBO_RANK):
        combo_rank_data.append((
            combo_rank,
            stats.fc_dist[i] / stats.count,
            sum(stats.fc_dist[i:]) / stats.count,
            level_stats.fc_dist[i],
            sum(level_stats.fc_dist[i:]),
            # stats.fc_dist[i] / stats.count - level_stats.fc_dist[i],
            # sum(stats.fc_dist[i:]) / stats.count - sum(level_stats.fc_dist[i:]),
        ))

    return (
        f'''{music.id}. {music.title} | {DIFFICULTY_NAME[diff_index]} {music.ds[diff_index]}
# 斜杠后为合计值，小括号内为同等级平均值，中括号内为二者之差
【基础信息】
· 游玩次数：        {stats.count} ({level_stats.avg_count:.2f}) [{stats.count - level_stats.avg_count:+.2f}] [{stats.count / level_stats.avg_count - 1:+.2%}]
· 定数：            {music.ds[diff_index]:.1f}
· 拟合定数：        {stats.fit_diff:.2f}
· 平均达成率：      {stats.avg_achievement:.4f}% ({level_stats.avg_achievement:.4f}%) [{stats.avg_achievement - level_stats.avg_achievement:+.4f}%]
· 达成率标准差：    {get_std_dev_text(stats.std_dev)} {stats.std_dev:.2f}% ({level_stats.avg_std_dev:.2f}%) [{stats.std_dev - level_stats.avg_std_dev:+.2f}%]
· 平均DX分数：      {stats.avg_dx_score:.2f}
· 平均DX分数比例：  {stats.avg_dx_score / chart.max_dx_score:.2%} ({level_stats.avg_dx_score_ratio:.2%}) [{stats.avg_dx_score / chart.max_dx_score - level_stats.avg_dx_score_ratio:+.2%}]
· SSS占比：         {score_rank_data[12][2]:.2%} ({score_rank_data[12][4]:.2%}) [{score_rank_data[12][2] - score_rank_data[12][4]:+.2%}]
· SSS+占比：        {score_rank_data[13][2]:.2%} ({score_rank_data[13][4]:.2%}) [{score_rank_data[13][2] - score_rank_data[13][4]:+.2%}]
· FC占比：          {combo_rank_data[1][2]:.2%} ({combo_rank_data[1][4]:.2%}) [{combo_rank_data[1][2] - combo_rank_data[1][4]:+.2%}]
· AP占比：          {combo_rank_data[3][2]:.2%} ({combo_rank_data[3][4]:.2%}) [{combo_rank_data[3][2] - combo_rank_data[3][4]:+.2%}]

【达成率分布】
'''
        + '\n'.join(f'· {r:6}{a:7.2%} /{b:7.2%} ({c:7.2%} /{d:7.2%}) [{a-c:+7.2%} /{b-d:+7.2%}]' for r, a, b, c, d in reversed(score_rank_data))
        + '''

【全连分布】
'''
        + '\n'.join(f'· {r:6}{a:7.2%} /{b:7.2%} ({c:7.2%} /{d:7.2%}) [{a-c:+7.2%} /{b-d:+7.2%}]' for r, a, b, c, d in reversed(combo_rank_data))
    )
