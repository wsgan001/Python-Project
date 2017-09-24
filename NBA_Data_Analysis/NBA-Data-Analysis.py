
# coding: utf-8

# ## 1. 导入相关模块

# In[1]:

import pandas as pd
import numpy as np
import math
import csv
import random
from sklearn import linear_model
from sklearn.model_selection import cross_val_score


# ## 2. 设置回归训练时的参数变量

# In[2]:

# 当每支队伍没有Elo等级分时，赋予其基础Elo等级分
base_elo = 1600
team_elos = {}
team_stats = {}
X = []
y = []
folder = 'data'    # 存放数据的目录


# ## 3. 数据清洗 & 属性列连接

# In[4]:

# 根据每支队伍的Miscellaneous Opponent Team 统计数据csv文件进行初始化
def initialize_data(Mstat, Ostat, Tstat):
    new_Mstat = Mstat.drop(['Rk', 'Arena'], axis=1)
    new_Ostat = Ostat.drop(['Rk', 'G', 'MP'], axis=1)
    new_Tstat = Tstat.drop(['Rk', 'G', 'MP'], axis=1)
    
    team_stats1 = pd.merge(new_Mstat, new_Ostat, how='left', on='Team')
    team_stats1 = pd.merge(team_stats1, new_Tstat, how='left', on='Team')
    
    return team_stats1.set_index('Team', inplace=False, drop=True)


# ## 4. 初始elo赋值函数

# In[6]:

def get_elo(team):
    try:
        return team_elos[team]
    except:
        # 当最初没有elo时，给每个队伍最初赋值base_elo
        team_elos[team] = base_elo
        return team_elos[team]


# ## 5. 定义Elo等级分函数

# In[14]:

# 计算每个球队的elo值
def calc_elo(win_team, lose_team):
    winner_rank = get_elo(win_team)
    loser_rank = get_elo(lose_team)
    
    rank_diff = winner_rank - loser_rank
    exp = - rank_diff/400
    odds = 1/(1 + math.pow(10,exp))
    
    # 根据rank级别修改K值
    if winner_rank < 2100:
        k = 32
    elif winner_rank >=  2100 and winner_rank < 2400:
        k = 24
    else:
        k = 16
    
    new_winner_rank = round(winner_rank + (k*(1-odds)))
    new_rank_diff = new_winner_rank - winner_rank
    new_loser_rank = loser_rank - new_rank_diff
    
    return new_winner_rank, new_loser_rank


# ## 6. 建立数据集

# In[27]:

def build_dataSet(all_data):
    print("Building data set ...")
    X = []
    y = []
    skip = 0
    for index, row in all_data.iterrows():
        Wteam = row['WTeam']
        Lteam = row['LTeam']
        
        # 获取最初的elo或是每个队伍最初的elo值
        team1_elo = get_elo(Wteam)
        team2_elo = get_elo(Lteam)
        
        # 给主场比赛的队伍加上100的elo值
        if row['WLoc'] == 'H':
            team1_elo += 100
        else:
            team2_elo += 100
            
        # 把elo当为评价每个队伍的第一个特征值
        team1_features = [team1_elo]
        team2_features = [team2_elo]
        
        
        # 添加我们从basketball reference.com获得的每个队伍的统计信息
        for key, value in team_stats.loc[Wteam].iteritems():
            team1_features.append(value)
        for key, value in team_stats.loc[Lteam].iteritems():
            team2_features.append(value)
            
        # 将两支队伍的特征值随机分配在每场比赛数据的左右两侧，并将对应的0/1赋给y
        if random.random() > 0.5:
            X.append(team1_features + team2_features)
            y.append(0)
        else:
            X.append(team2_features + team1_features)
            y.append(1)
        
        if skip == 0:
            print(X)
            skip = 1
        
        # 根据这场比赛的数据更新队伍的elo值
        new_winner_rank, new_loser_rank = calc_elo(Wteam, Lteam)
        team_elos[Wteam] = new_winner_rank
        team_elos[Lteam] = new_loser_rank
        
    return np.nan_to_num(X), y


# ## 7. main 函数调用，建立Logistic Regression回归模型

# In[28]:

if __name__ == '__main__':
    Mstat = pd.read_csv(folder + '/15-16Miscellaneous_Stat.csv')
    Ostat = pd.read_csv(folder + '/15-16Opponent_Per_Game_Stat.csv')
    Tstat = pd.read_csv(folder + '/15-16Team_per_Game_Stat.csv')
    
    team_stats = initialize_data(Mstat, Ostat, Tstat)
    result_data = pd.read_csv(folder + '/2015-2016_result.csv')
    
    X, y = build_dataSet(result_data)
    
    # 训练网络模型
    print("Fitting on %d game samples ..." % len(X))
    
    model = linear_model.LogisticRegression()
    model.fit(X, y)
    
    # 利用10折交叉验证计算训练正确率
    print("Doing cross-validation ...")
    print(cross_val_score(model, X, y, cv=10, scoring='accuracy', n_jobs=-1).mean())
    


# ## 8. 比赛胜率预测函数

# In[35]:

def predict_winner(team_1, team_2, model):
    features = []
    
    # team 1: 客场队伍
    features.append(get_elo(team_1))
    for key, value in team_stats.loc[team_1].iteritems():
        features.append(value)
    
    # team 2: 主场队伍
    features.append(get_elo(team_2) + 100)
    for key, value in team_stats.loc[team_2].iteritems():
        features.append(value)
        
    features = np.nan_to_num(features)
    return model.predict_proba([features])


# ## 9. 利用训练好的模型在16-17赛季的比赛中进行预测

# In[61]:

print('Predicting on new season ...')
season_new = pd.read_csv(folder + '/16-17Schedule.csv')
result = []

for index, row in season_new.iterrows():
    team1 = row['Vteam']
    team2 = row['Hteam']
    pred = predict_winner(team1, team2, model)
    prob = pred[0][0]
    
    if prob > 0.5:
        winner = team1
        loser = team2
        result.append([winner, loser, prob])
    else:
        winner = team2
        loser = team1
        result.append([winner, loser, 1-prob])
        
    with open('16-17Result.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(["win", "lose", "probability"])
        writer.writerows(result)


# %ls 16-17Result.csv data prediction.py