DIFFICULTY_NAME: list[str] = ['Basic', 'Advanced', 'Expert', 'Master', 'Re:MASTER']
'''`['Basic', 'Advanced', 'Expert', 'Master', 'Re:MASTER']`'''

score_rank: list[str] = ['d', 'c', 'b', 'bb', 'bbb', 'a', 'aa', 'aaa', 's', 'sp', 'ss', 'ssp', 'sss', 'sssp']
'''`['d', 'c', 'b', 'bb', 'bbb', 'a', 'aa', 'aaa', 's', 'sp', 'ss', 'ssp', 'sss', 'sssp']`'''

SCORE_RANK: list[str] = ['D', 'C', 'B', 'BB', 'BBB', 'A', 'AA', 'AAA', 'S', 'S+', 'SS', 'SS+', 'SSS', 'SSS+']
'''`['D', 'C', 'B', 'BB', 'BBB', 'A', 'AA', 'AAA', 'S', 'S+', 'SS', 'SS+', 'SSS', 'SSS+']`'''

COMBO_RANK: list[str] = ['Not FC', 'FC', 'FC+', 'AP', 'AP+']
'''`['Not FC', 'FC', 'FC+', 'AP', 'AP+']`'''

combo_rank: list[str] = ['', 'fc', 'fcp', 'ap', 'app']
'''`['', 'fc', 'fcp', 'ap', 'app']`'''

SYNC_RANK: list[str] = ['Not FS', 'FS', 'FS+', 'FSD', 'FSD+']
'''`['Not FS', 'FS', 'FS+', 'FSD', 'FSD+']`'''

sync_rank: list[str] = ['', 'fs', 'fsp', 'fsd', 'fsdp']
'''`['', 'fs', 'fsp', 'fsd', 'fsdp']`'''

LEVELS: list[str] = ['1', '2', '3', '4', '5', '6', '7', '7+', '8', '8+', '9', '9+', '10', '10+', '11', '11+', '12', '12+', '13', '13+', '14', '14+', '15']
'''`['1', '2', '3', '4', '5', '6', '7', '7+', '8', '8+', '9', '9+', '10', '10+', '11', '11+', '12', '12+', '13', '13+', '14', '14+', '15']`'''

achievementList: list[float] = [50.0, 60.0, 70.0, 75.0, 80.0, 90.0, 94.0, 97.0, 98.0, 99.0, 99.5, 100.0, 100.5]
'''`[50.0, 60.0, 70.0, 75.0, 80.0, 90.0, 94.0, 97.0, 98.0, 99.0, 99.5, 100.0, 100.5]`'''

BaseRa: list[float] = [0.0, 5.0, 6.0, 7.0, 7.5, 8.5, 9.5, 10.5, 12.5, 12.7, 13.0, 13.2, 13.5, 14.0]
'''`[0.0, 5.0, 6.0, 7.0, 7.5, 8.5, 9.5, 10.5, 12.5, 12.7, 13.0, 13.2, 13.5, 14.0]`'''

BaseRaSpp: list[float] = [7.0, 8.0, 9.6, 11.2, 12.0, 13.6, 15.2, 16.8, 20.0, 20.3, 20.8, 21.1, 21.6, 22.4]
'''`[7.0, 8.0, 9.6, 11.2, 12.0, 13.6, 15.2, 16.8, 20.0, 20.3, 20.8, 21.1, 21.6, 22.4]`'''

VERSION_TO_PLATE: dict[str, str] = {
    'maimai': '真',
    'maimai PLUS': '真',
    'maimai GreeN': '超',
    'maimai GreeN PLUS': '檄',
    'maimai ORANGE': '橙',
    'maimai ORANGE PLUS': '暁',
    'maimai PiNK': '桃',
    'maimai PiNK PLUS': '櫻',
    'maimai MURASAKi': '紫',
    'maimai MURASAKi PLUS': '菫',
    'maimai MiLK': '白',
    'MiLK PLUS': '雪',
    'maimai FiNALE': '輝',
    'maimai でらっくす': '熊',
    'maimai でらっくす PLUS': '華',
    'maimai でらっくす Splash': '爽',
    'maimai でらっくす Splash PLUS': '煌',
    'maimai でらっくす UNiVERSE': '宙',
    'maimai でらっくす UNiVERSE PLUS': '星',
    'maimai でらっくす FESTiVAL': '祭',
}
'''
```
{
    'maimai': '真',
    'maimai PLUS': '真',
    'maimai GreeN': '超',
    'maimai GreeN PLUS': '檄',
    'maimai ORANGE': '橙',
    'maimai ORANGE PLUS': '暁',
    'maimai PiNK': '桃',
    'maimai PiNK PLUS': '櫻',
    'maimai MURASAKi': '紫',
    'maimai MURASAKi PLUS': '菫',
    'maimai MiLK': '白',
    'MiLK PLUS': '雪',
    'maimai FiNALE': '輝',
    'maimai でらっくす': '熊',
    'maimai でらっくす PLUS': '華',
    'maimai でらっくす Splash': '爽',
    'maimai でらっくす Splash PLUS': '煌',
    'maimai でらっくす UNiVERSE': '宙',
    'maimai でらっくす UNiVERSE PLUS': '星',
    'maimai でらっくす FESTiVAL': '祭',
}
```
'''

PLATE_TO_VERSION: dict[str, list[str]] = {
    '真': ['maimai', 'maimai PLUS'],
    '超': ['maimai GreeN'],
    '檄': ['maimai GreeN PLUS'],
    '橙': ['maimai ORANGE'],
    '暁': ['maimai ORANGE PLUS'],
    '晓': ['maimai ORANGE PLUS'],
    '桃': ['maimai PiNK'],
    '櫻': ['maimai PiNK PLUS'],
    '樱': ['maimai PiNK PLUS'],
    '紫': ['maimai MURASAKi'],
    '菫': ['maimai MURASAKi PLUS'],
    '堇': ['maimai MURASAKi PLUS'],
    '白': ['maimai MiLK'],
    '雪': ['MiLK PLUS'],
    '輝': ['maimai FiNALE'],
    '辉': ['maimai FiNALE'],
    '舞': ['maimai', 'maimai PLUS', 'maimai GreeN',
          'maimai GreeN PLUS', 'maimai ORANGE', 'maimai ORANGE PLUS',
          'maimai PiNK', 'maimai PiNK PLUS', 'maimai MURASAKi',
          'maimai MURASAKi PLUS', 'maimai MiLK', 'MiLK PLUS',
          'maimai FiNALE'],
    '霸': ['maimai', 'maimai PLUS', 'maimai GreeN',
          'maimai GreeN PLUS', 'maimai ORANGE', 'maimai ORANGE PLUS',
          'maimai PiNK', 'maimai PiNK PLUS', 'maimai MURASAKi',
          'maimai MURASAKi PLUS', 'maimai MiLK', 'MiLK PLUS',
          'maimai FiNALE'],
    '熊': ['maimai でらっくす'],
    '華': ['maimai でらっくす PLUS'],
    '华': ['maimai でらっくす PLUS'],
    '爽': ['maimai でらっくす Splash'],
    '煌': ['maimai でらっくす Splash PLUS'],
    '宙': ['maimai でらっくす UNiVERSE'],
    '星': ['maimai でらっくす UNiVERSE PLUS'],
    '祭': ['maimai でらっくす FESTiVAL'],
}
