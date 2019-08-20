# coding=utf-8
""""
    Item Based Collaborative Filtering Recommender (Item KNN)
    [Item Recommendation (Ranking)]

    Item KNN predicts a user’s ranking based on similar items which him/her access.

"""

# © 2019. Case Recommender (MIT License)

from collections import defaultdict
import numpy as np

from caserec.recommenders.item_recommendation.base_item_recommendation import BaseItemRecommendation
from caserec.utils.extra_functions import timed

__author__ = 'Arthur Fortes <fortes.arthur@gmail.com>'


class ItemKNN(BaseItemRecommendation):
    def __init__(self, train_file=None, test_file=None, output_file=None, similarity_metric="cosine", k_neighbors=None,
                 rank_length=10, as_binary=False, as_similar_first=True, sep='\t', output_sep='\t'):

        """
        Item KNN for Item Recommendation

        This algorithm predicts a rank for each user based on the similar items that he/her consumed.

        Usage::

            >> ItemKNN(train, test, as_similar_first=True).compute()
            >> ItemKNN(train, test, ranking_file, as_binary=True).compute()

        :param train_file: File which contains the train set. This file needs to have at least 3 columns
        (user item feedback_value).
        :type train_file: str

        :param test_file: File which contains the test set. This file needs to have at least 3 columns
        (user item feedback_value).
        :type test_file: str, default None

        :param output_file: File with dir to write the final predictions
        :type output_file: str, default None

        :param similarity_metric: Pairwise metric to compute the similarity between the items. Reference about
        distances: http://docs.scipy.org/doc/scipy-0.14.0/reference/generated/scipy.spatial.distance.pdist.html
        :type similarity_metric: str, default cosine

        :param k_neighbors: Number of neighbors to use. If None, k_neighbor = int(sqrt(n_items))
        :type k_neighbors: int, default None

        :param rank_length: Size of the rank that must be generated by the predictions of the recommender algorithm
        :type rank_length: int, default 10

        :param as_binary: If True, the explicit feedback will be transform to binary
        :type as_binary: bool, default False

        :param as_similar_first: If True, for each unknown item, which will be predicted, we first look for its k
        most similar users and then take the intersection with the users that
        seen that item.
        :type as_similar_first: bool, default True

        :param sep: Delimiter for input files
        :type sep: str, default '\t'

        :param output_sep: Delimiter for output file
        :type output_sep: str, default '\t'

        """

        super(ItemKNN, self).__init__(train_file=train_file, test_file=test_file, output_file=output_file,
                                      as_binary=as_binary, rank_length=rank_length, similarity_metric=similarity_metric,
                                      sep=sep, output_sep=output_sep)

        self.recommender_name = 'ItemKNN Algorithm'

        self.as_similar_first = as_similar_first
        self.k_neighbors = k_neighbors

        # internal vars
        self.si_matrix = None
        self.similar_items = None

    def init_model(self):
        """
        Method to initialize the model. Create and calculate a similarity matrix

        """
        self.similar_items = defaultdict(list)

        # Set the value for k
        if self.k_neighbors is None:
            self.k_neighbors = int(np.sqrt(len(self.items)))

        self.create_matrix()
        self.si_matrix = self.compute_similarity(transpose=True)

        for i_id, item in enumerate(self.items):
            self.similar_items[i_id] = sorted(range(len(self.si_matrix[i_id])),
                                              key=lambda k: -self.si_matrix[i_id][k])[1:self.k_neighbors + 1]

    def predict(self):
        """
        This method predict a rank for a specific user.

        """

        for u_id, user in enumerate(self.users):
            if len(self.train_set['feedback'].get(user, [])) != 0:
                if self.as_similar_first:
                    self.ranking += self.predict_similar_first_scores(user, u_id)
                else:
                    self.ranking += self.predict_scores(user, u_id)

            else:
                # Implement cold start user
                pass

    def predict_scores(self, user, user_id):
        partial_predictions = []
        # Selects items that user has not interacted with.
        u_list = list(np.flatnonzero(self.matrix[user_id] == 0))
        seen_items_id = np.flatnonzero(self.matrix[user_id])

        # predict score for item_i
        for i_id in u_list:
            sim_sum = sorted(np.take(self.si_matrix[i_id], seen_items_id), key=lambda x: -x)
            partial_predictions.append((user, self.items[i_id], sum(sim_sum[:self.k_neighbors])))

        return sorted(partial_predictions, key=lambda x: -x[2])[:self.rank_length]

    def predict_similar_first_scores(self, user, user_id):
        """
        In this implementation, for each unknown item, which will be
        predicted, we first look for its k most similar items and then take the intersection with the seen items of
        the user. Finally, the score of the unknown item will be the sum of the  similarities of k's most similar
        to it, taking into account only the items that each user seen.

        """

        predictions = []

        # Selects items that user has not interacted with.
        u_list = list(np.flatnonzero(self.matrix[user_id] == 0))
        seen_items_id = np.flatnonzero(self.matrix[user_id])

        # predict score for item_i
        for i_id in u_list:
            # s_id = list(filter(set(self.similar_items[i]).__contains__, seen_items_id))
            s_id = list(set(self.similar_items[i_id]).intersection(seen_items_id))
            sim_sum = np.take(self.si_matrix[i_id], s_id)
            predictions.append((user, self.items[i_id], sum(sim_sum)))

        return sorted(predictions, key=lambda x: -x[2])[:self.rank_length]

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

        super(ItemKNN, self).compute(verbose=verbose)

        if verbose:
            print("training_time:: %4f sec" % timed(self.init_model))
            if self.extra_info_header is not None:
                print(self.extra_info_header)
            print("prediction_time:: %4f sec" % timed(self.predict))
            print('\n')

        else:
            self.init_model()
            self.predict()

        self.write_ranking()

        if self.test_file is not None:
            self.evaluate(metrics, verbose_evaluation, as_table=as_table, table_sep=table_sep, n_ranks=n_ranks)
