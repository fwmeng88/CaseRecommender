# coding=utf-8
""""
    Content Based Recommender.

    Literature:
    Guangyuan Piao and John G. Breslin. 2016. Measuring semantic distance for linked open data-enabled recommender
    systems. In Proceedings of the 31st Annual ACM Symposium on Applied Computing (SAC '16). ACM, New York, NY, USA,
    315-320. DOI: https://doi.org/10.1145/2851613.2851839

"""

# © 2019. Case Recommender (MIT License)

import numpy as np

from caserec.recommenders.item_recommendation.base_item_recommendation import BaseItemRecommendation
from caserec.utils.process_data import ReadFile
from caserec.utils.extra_functions import timed

__author__ = 'Eduardo Fressato <eduardofressato@hotmail.com>'


class ContentBased(BaseItemRecommendation):
    def __init__(self, train_file=None, test_file=None, output_file=None, similarity_file=None, similarity_sep='\t',
                 rank_length=10, as_binary=True, sep='\t', output_sep='\t'):

        """
        Content Based Recommender for Item Recommendation

        Usage::

            >> ContentBased(train, test, similarity_file=similarity_file).compute()

        :param train_file: File which contains the train set. This file needs to have at least 3 columns
        (user item feedback_value).
        :type train_file: str

        :param test_file: File which contains the test set. This file needs to have at least 3 columns
        (user item feedback_value).
        :type test_file: str, default None

        :param output_file: File with dir to write the final predictions
        :type output_file: str, default None

        :param similarity_file: File which contains the similarity set. This file needs to have at least 3 columns
        (item item similarity).
        :type similarity_file: str, default None

        :param rank_length: Size of the rank that must be generated by the predictions of the recommender algorithm
        :type rank_length: int, default 10

        :param similarity_sep: Delimiter for similarity or metadata file
        :type similarity_sep: str, default '\t'

        :param sep: Delimiter for input files file
        :type sep: str, default '\t'

        :param output_sep: Delimiter for output file
        :type output_sep: str, default '\t'

        """

        super(ContentBased, self).__init__(train_file=train_file, test_file=test_file, output_file=output_file,
                                           as_binary=as_binary, rank_length=rank_length, sep=sep, output_sep=output_sep)

        self.recommender_name = 'Content Based Algorithm'

        self.similarity_file = similarity_file
        self.similarity_sep = similarity_sep
        self.si_matrix = None
        self.similar_items = None

        self.users_profile = None

    def init_model(self):
        """
        Method to initialize the model. Create and read a similarity matrix

        """
        if self.similarity_file is not None:
            similarity = ReadFile(self.similarity_file, sep=self.similarity_sep, as_binary=False
                                  ).read_metadata_or_similarity()

            self.si_matrix = np.zeros((len(self.items), len(self.items)))

            # Fill similarity matrix
            for i in similarity['col_1']:
                for i_j in similarity['dict'][i]:
                    self.si_matrix[self.item_to_item_id[i], self.item_to_item_id[int(i_j)]] = similarity['dict'][i][i_j]

            # Remove NaNs
            self.si_matrix[np.isnan(self.si_matrix)] = 0.0

        else:
            raise ValueError("This algorithm needs a similarity matrix file!")

    def create_user_profile(self):
        self.users_profile = self.train_set['items_seen_by_user']

    def predict(self):
        for u in self.train_set['users']:
            self.ranking += self.predict_user_rank(u)

    def predict_user_rank(self, user):
        unseen_items = set(self.items).difference(self.users_profile[user])

        list_scores = []
        for i in unseen_items:
            list_scores.append(self.predict_item_score(user, i))

        return sorted(list_scores, key=lambda x: -x[2])[:self.rank_length]

    def predict_item_score(self, user, item):
        sum_sim = 0
        for i in self.users_profile[user]:
            sum_sim += self.si_matrix[self.item_to_item_id[item]][self.item_to_item_id[i]]

        return [user, item, sum_sim / len(self.users_profile[user])]

    def compute(self, verbose=True, metrics=None, verbose_evaluation=True, as_table=False, table_sep='\t', n_ranks=None):
        """
        Extends compute method from BaseItemRecommendation. Method to run recommender algorithm

        :param verbose: Print recommender and database information
        :type verbose: bool, default True

        :param metrics: List of evaluation metrics
        :type metrics: list, default None

        :param verbose_evaluation: Print the evaluation results
        :type verbose_evaluation: bool, default True

        :param as_table: Print the evaluation results as table
        :type as_table: bool, default False

        :param table_sep: Delimiter for print results (only work with verbose=True and as_table=True)
        :type table_sep: str, default '\t'

        :param n_ranks: List of positions to evaluate the ranking
        :type n_ranks: list, None

        """

        super(ContentBased, self).compute(verbose=verbose)

        if verbose:
            print("training_time:: %4f sec" % timed(self.init_model))
            if self.extra_info_header is not None:
                print(self.extra_info_header)

            self.create_user_profile()
            print("prediction_time:: %4f sec" % timed(self.predict))
            print('\n')
        else:
            self.init_model()
            self.create_user_profile()
            self.predict()

        self.write_ranking()

        if self.test_file is not None:
            self.evaluate(metrics, verbose_evaluation, as_table=as_table, table_sep=table_sep, n_ranks=n_ranks)
