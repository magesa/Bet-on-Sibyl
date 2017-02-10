# coding: utf-8

# In[1]:

import datetime as dt
import sys

import dateutil.relativedelta
from pandas import *


# get_ipython().magic(u'matplotlib inline')

class ModelMetricsFootballTop5(object):
    # -----------!!!! You have to manually configure the category string variable in the script !!! ---------------

    def __init__(self, tableau_input_filename, category, leagues, cs_team_stats_filename):
        # leagues is upcoming games from scrape_matchup_datetime... 
        # => list of csv files extension ex : Bundesliga, Serie_A, Primera_Division
        self.tableau_input_filename = tableau_input_filename
        self.category = category
        self.leagues = leagues
        self.cs_team_stats_filename = cs_team_stats_filename

    def __call__(self):
        self.get_metrics(self.tableau_input_filename, self.category, self.leagues, self.cs_team_stats_filename)

    def get_metrics(self, tableau_input_filename, category, leagues, cs_team_stats_filename):

        big_df = read_csv(tableau_input_filename)

        category = [category]
        leagues.extend(category)

        for league in leagues:

            # Creating a df for each league for level 2 pages

            if league == 'FootballTop5':
                df = big_df
            else:
                df = big_df.loc[big_df['League_T'] == league.replace("_", "-").lower()]

            df['Confidence'] = df['Confidence'].round(3)
            df = df.sort_values('Date')
            df = df.drop('ID', axis=1)
            df = df.reset_index(drop=True)
            df['Date'] = to_datetime(df['Date'], format='%Y-%m-%d')
            # Adding the current datetime
            current_date = dt.datetime.today().strftime("%m/%d/%Y")

            # Replacing the 1s and 0s by the team names for predictions and results
            df['Predicted_Result'] = df.apply(
                lambda x: x['Home_Team'] if x['Predicted_Result'] == 1 else
                x['Visitor_Team'] if x[
                                         'Predicted_Result'] == 2 else 'Draw' if
                x['Predicted_Result'] == 0 else 0, axis=1)
            df['True_Result'] = df.apply(lambda x: x['Home_Team'] if x['True_Result'] == 1 \
                else x['Visitor_Team'] if x['True_Result'] == 2 else 'Draw' if x['True_Result'] == 0 else 0, axis=1)

            # Calculating the number of games for the current date
            today_games = df[(df['Date'] == current_date)]
            n_today_games = len(today_games)

            # Calculating the number of predictions made so far by Sibyl
            predictions_sofar = df[(df['Date'] <= current_date)]
            predictions_sofar = predictions_sofar.sort_values('Date')
            n_predictions_sofar = len(predictions_sofar)

            # Calculating the % of correct predictions made by Sibyl
            #  based on all the previous games until current date (excluded)
            previous_games_df = df[(df['Date'] < current_date)]
            n_previous_games = len(previous_games_df)
            correct_predictions_df = previous_games_df[
                (previous_games_df['True_Result'] == previous_games_df['Predicted_Result'])]
            n_correct_pred = len(correct_predictions_df)
            perc_correct_pred = ((n_correct_pred / float(n_previous_games)) * 100)
            perc_correct_pred = float(format(perc_correct_pred, '.2f'))

            # Creating a df composed of games from one month ago until current date minus one day
            # -> filtered on games where Sibyl was right
            current_date_type_datetime = to_datetime(current_date, format="%m/%d/%Y")
            current_date_minus_one_month = current_date_type_datetime - dateutil.relativedelta.relativedelta(months=1,
                                                                                                             days=1)
            one_month_games_df = df[(df['Date'] < current_date) & (df['Date'] >= current_date_minus_one_month)]
            correct_predictions_one_month_ago_df = one_month_games_df[
                (one_month_games_df['True_Result'] == one_month_games_df['Predicted_Result'])]

            # -------------------------------------------------------------------------------------------------------
            # Taking the current season team stats df to take the list of teams
            cs_team_stats_df = read_csv(cs_team_stats_filename)
            db_team_names_list = sorted(cs_team_stats_df['Tm'].tolist())
            teams = db_team_names_list

            # Determining the team of the month to bet on
            # When Sibyl tells they will win and they win... -> nb: % of win games in this case since one month
            best_team_as_chosen = ''
            best__perc_as_chosen = 0.0

            for team in teams:
                try:
                    n_games_played_at_home = one_month_games_df.Home_Team.str.contains(team).sum()
                    n_games_played_away = one_month_games_df.Visitor_Team.str.contains(team).sum()
                    n_games_played = n_games_played_at_home + n_games_played_away

                    wins_as_chosen = correct_predictions_one_month_ago_df.True_Result.str.contains(team).sum()

                    perc_wins = (wins_as_chosen / float(n_games_played)) * 100
                    perc_wins = float(format(perc_wins, '.2f'))

                except KeyError:
                    pass

                if wins_as_chosen == 0:
                    continue

                if perc_wins > best__perc_as_chosen:
                    best_team_as_chosen = team
                    best__perc_as_chosen = perc_wins

            # Creating a df composed of games from one month ago until current date minus one day
            # -> filtered on games where Sibyl was wrong
            mistakes_one_month_ago_df = one_month_games_df[
                (one_month_games_df['True_Result'] != one_month_games_df['Predicted_Result'])]
            # When Sibyl tells they will win and they end up to loose...
            # -> nb: % of lost games in this case since one month
            worst_team_as_chosen = ''

            worst__perc_as_chosen = 0.0

            for team in teams:
                try:
                    n_games_played_at_home = one_month_games_df.Home_Team.str.contains(team).sum()
                    n_games_played_away = one_month_games_df.Visitor_Team.str.contains(team).sum()
                    n_games_played = n_games_played_at_home + n_games_played_away

                    lost_games_as_chosen = mistakes_one_month_ago_df.Predicted_Result.str.contains(team).sum()

                    perc_lost_games = (lost_games_as_chosen / float(n_games_played)) * 100
                    perc_lost_games = float(format(perc_lost_games, '.2f'))

                except KeyError:
                    pass

                if lost_games_as_chosen == 0:
                    continue

                if perc_lost_games > worst__perc_as_chosen:
                    worst_team_as_chosen = team
                    worst__perc_as_chosen = perc_lost_games

            # --------------------------------------------------------------------------------------------------------------------
            # Getting the metrics dfs for each league set up at init 

            # Top teams to bet on based on divergence strategy for the next matchups nb: US Presentation
            today_games_df_us = read_csv(league + '_Upcoming_Matchups_US_P_df.csv')

            today_games_df_us['Date'] = to_datetime(today_games_df_us['Date'], format='%Y-%m-%d')

            today_games_divstrat_df = today_games_df_us[(today_games_df_us['Divergence_Y/N'] == 'Y') & (
                today_games_df_us['Date'].dt.day >= current_date_type_datetime.day)]
            today_games_divstrat_df = today_games_divstrat_df.sort_values(['Date', 'Time'], ascending=True)
            today_games_divstrat_df = today_games_divstrat_df.drop_duplicates('Matchup_US_P')

            # Calculating the mean confidence of Sibyl in the case of divergence games
            mean_sibyl_conf_for_divstrat = today_games_divstrat_df['Confidence'].mean()

            # Putting the calculated values into dfs
            sibyl_metrics_df = DataFrame(
                columns=['N_Today_games', 'N_Predictions_made', 'Sea_Perc_corr_pred', 'Mean_Sibyl_conf_for_divstrat'])
            month_teams_df = DataFrame(
                columns=['Team_of_the_month', 'Best_percent_as_chosen', 'Worst_team_of_the_month',
                         'Worst_perc_as_chosen'])
            today_games_divstrat_df = today_games_divstrat_df

            sibyl_metrics_df['N_Today_games'] = n_today_games
            sibyl_metrics_df['N_Predictions_made'] = n_predictions_sofar
            sibyl_metrics_df['Sea_Perc_corr_pred'] = perc_correct_pred
            sibyl_metrics_df['Mean_Sibyl_conf_for_divstrat'] = mean_sibyl_conf_for_divstrat

            month_teams_df['Team_of_the_month'] = best_team_as_chosen
            month_teams_df['Best_percent_as_chosen'] = best__perc_as_chosen

            month_teams_df['Worst_team_of_the_month'] = worst_team_as_chosen
            month_teams_df['Worst_perc_as_chosen'] = worst__perc_as_chosen

            sibyl_metrics_df.loc[len(sibyl_metrics_df)] = [n_today_games, n_predictions_sofar, perc_correct_pred,
                                                           mean_sibyl_conf_for_divstrat]
            month_teams_df.loc[len(month_teams_df)] = [best_team_as_chosen, best__perc_as_chosen, worst_team_as_chosen,
                                                       worst__perc_as_chosen]

            sibyl_metrics_df.to_csv('Sibyl_metrics_' + league + '.csv', mode='w+', index=True)
            month_teams_df.to_csv('Month_teams_' + league + '.csv', mode='w+', index=True)
            today_games_divstrat_df.to_csv('today_games_divstrat_' + league + '.csv', mode='w+', index=True)

            self.sibyl_metrics_df = sibyl_metrics_df
            self.month_teams_df = month_teams_df
            self.today_games_divstrat_df = today_games_divstrat_df
            self.df = df

            # The final  table output are:
            # "sibyl_metrics_df", "month_teams_df", "today_games_divstrat_df"
if __name__ == '__main__':

    x = ModelMetricsFootballTop5("football_top5_tableau_output_2017.csv",'FootballTop5',\
    ['Bundesliga', 'Primera_Division', 'Serie_A', 'Premier_League', 'Ligue_1'],\
    "football_top5_team_stats_2017_2017.csv")
    x()