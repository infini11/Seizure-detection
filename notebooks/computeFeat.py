import numpy as np
import pandas as pd

from hrvanalysis import (
    remove_outliers,
    remove_ectopic_beats,
    interpolate_nan_values,
    get_time_domain_features,
    get_csi_cvi_features,
    get_sampen,
    get_poincare_plot_features,
    get_frequency_domain_features,
)


class compute_features:
    """
    Compute hrvanalysis features in attribute "features".

    This class compute Heart Rate Variability features based on detected
    RR-intervals. Some features are efficent only on some time periods,
    therefore there are 3 time windows to compute when time availiable is
    long enough. A sliding time window allows to scroll through timeline to
    to compute at different start points.

    *compute* method is used to compute all possible features directly. They
    will be stored in attribute *features*.
    """

    def __init__(
        self,
        rr_timestamps: np.array,
        rr_intervals: np.array,
        features_key_to_index: dict,
        sliding_window: int,
        short_window: int,
        medium_window: int,
        large_window: int,
    ):
        """
        Initialize all required attributes to compute Heart Rate Variation.

        Parameters
        ----------
        rr_timestamps : np.array
            Computed RR intervals timestamps as an array
        rr_intervals : np.array
            RR intervals are each timestamps as an array
        features_key_to_index : dict
            Features to index as a dictionnary. Needed to add data at the right
            position
        sliding_window : int
            Period in milliseconds that will be used to slide on the timeline
        short_window : int
            Size of the short time window, in milliseconds, which fits to
            compute time domain features
        medium_window : int
            Size of the medium time window, in milliseconds, which fits to
            compute
        large_window : int
            Size of the large time window, in milliseconds, which fits to
            compute non linear features
        """
        # Sets arguments as class attributes
        self.__dict__.update(locals())

        # Compute quantity of short intervals to iterate
        self.n_short_intervals = int((self.rr_timestamps[-1] / self.sliding_window) + 1)

        # Initialize "features" variable to store results
        self.features = np.empty(
            [self.n_short_intervals, len(self.features_key_to_index.keys())]
        )
        self.features[:] = np.NaN

        # Computes hrv features and store them in variable "features"
        self.compute()

    def compute(self):
        """
        Compute possible all features.

        According to different threshold, compute possible features from
        hrvanalysis:
        * time domain
        * non linear
        * frequency domain
        These features are stored in class attribute "features".
        """
        for _index in range(self.n_short_intervals):

            (
                self.features[_index][self.features_key_to_index["interval_index"]]
            ) = _index

            (
                self.features[_index][self.features_key_to_index["interval_start_time"]]
            ) = (_index * self.sliding_window)

            for _size in ["short", "medium", "large"]:
                _window_size = self.__dict__[f"{_size}_window"]
                if (_index * self.sliding_window) >= _window_size:
                    # >= ou >(intialement) ?
                    _rr_on_intervals = self.get_rr_intervals_on_window(
                        index=_index, size=_size
                    )

                    # Handling to improve
                    if len(_rr_on_intervals) == 0:
                        print("No RR intervals")
                        continue

                    _clean_rrs = self.get_clean_intervals(_rr_on_intervals)
                    if _size == "short":
                        self.compute_time_domain_features(_index, _clean_rrs)
                    elif _size == "medium":
                        self.compute_non_linear_features(_index, _clean_rrs)
                    elif _size == "large":
                        self.compute_frequency_domain_features(_index, _clean_rrs)

    def get_rr_intervals_on_window(self, index: int, size: str) -> np.array:
        """
        Filter RR interval corresponding to a time window before index.

        Parameters
        ----------
        index : int
            Index of the timeline splitted by sliding window size
        size : str
            Size of the window, choices are [small, medium, large]

        Returns
        -------
        rr_on_intervals : np.array
            RR intervals on the select time window.
        """
        starting_timestamp = index * self.sliding_window
        window = self.__dict__[f"{size}_window"]
        offset = starting_timestamp - window
        rr_indices = np.logical_and(
            self.rr_timestamps >= offset, self.rr_timestamps < starting_timestamp
        )

        rr_on_intervals = self.rr_intervals[rr_indices]

        return rr_on_intervals

    def get_clean_intervals(self, rr_intervals: np.array) -> np.array:
        """
        Clean and returns RR intervals.

        Parameters
        ----------
        rr_intervals : np.array
            RR intervals to clean as an array

        Returns
        -------
        interpolated_nn_intervals : np.array
            The same RR intervals cleaned from outliers
        """
        # Removes outliers from signal
        rr_intervals_without_outliers = remove_outliers(
            rr_intervals=rr_intervals, low_rri=300, high_rri=1800, verbose=False
        )

        # Replaces outliers nan values with linear interpolation
        interpolated_rr_intervals = interpolate_nan_values(
            rr_intervals=rr_intervals_without_outliers, interpolation_method="linear"
        )

        # Removes ectopic beats from signal
        nn_intervals_list = remove_ectopic_beats(
            rr_intervals=interpolated_rr_intervals, method="malik", verbose=False
        )

        # Replaces ectopic beats nan values with linear interpolation
        interpolated_nn_intervals = interpolate_nan_values(
            rr_intervals=nn_intervals_list
        )

        return interpolated_nn_intervals

    def compute_time_domain_features(self, index: int, clean_rrs: np.array):
        """
        Compute time domain features from HRVanalysis.

        These features are meant for short window features and are added to
        features attribute.

        Parameters
        ----------
        index : int
            Index of the timeline splitted by sliding window size
        clean_rrs : np.array
            Clean RR intervals
        """
        try:
            time_domain_features = get_time_domain_features(clean_rrs)
            for key in time_domain_features.keys():
                (
                    self.features[index][self.features_key_to_index[key]]
                ) = time_domain_features[key]

        except ZeroDivisionError:
            pass

        except Exception as e:
            print(
                f"Interval {str(index)} - "
                f"computation issue on short window features {str(e)}"
            )

    def compute_non_linear_features(self, index: int, clean_rrs: np.array):
        """
        Compute non linear features from HRVanalysis.

        These features are meant for medium window features and are added to
        features attribute.

        Parameters
        ----------
        index : int
            Index of the timeline splitted by sliding window size
        clean_rrs : np.array
            Clean RR intervals
        """
        try:
            cvi_csi_features = get_csi_cvi_features(clean_rrs)
            for _key in cvi_csi_features.keys():
                (
                    self.features[index][self.features_key_to_index[_key]]
                ) = cvi_csi_features[_key]

            sampen = get_sampen(clean_rrs)
            (self.features[index][self.features_key_to_index["sampen"]]) = sampen[
                "sampen"
            ]

            poincare_features = get_poincare_plot_features(clean_rrs)
            for key in poincare_features.keys():
                (
                    self.features[index][self.features_key_to_index[key]]
                ) = poincare_features[key]

        except Exception as e:
            print(
                f"Interval {str(index)} - "
                f"computation issue on medium window features {str(e)}"
            )

    def compute_frequency_domain_features(self, index: int, clean_rrs: np.array):
        """
        Compute frequency domain features from HRV analysis.

        These features are meant for large window features and are added to
        features attribute.

        Parameters
        ----------
        index : int
            Index of the timeline splitted by sliding window size
        clean_rrs : np.array
            Clean RR intervals
        """
        try:
            frequency_domain_features = get_frequency_domain_features(
                nn_intervals=clean_rrs
            )
            for _key in frequency_domain_features.keys():
                if _key in self.features_key_to_index:
                    (
                        self.features[index][self.features_key_to_index[_key]]
                    ) = frequency_domain_features[_key]
        except Exception as e:
            print(
                f"Interval {str(index)} - "
                f"computation issue on large window features {str(e)}"
            )

