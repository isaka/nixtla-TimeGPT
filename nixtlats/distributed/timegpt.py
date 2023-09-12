# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/distributed.timegpt.ipynb.

# %% auto 0
__all__ = []

# %% ../../nbs/distributed.timegpt.ipynb 2
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np
import pandas as pd
import fugue
import fugue.api as fa
from fugue.execution.factory import make_execution_engine
from triad import Schema

# %% ../../nbs/distributed.timegpt.ipynb 3
class _DistributedTimeGPT:
    def _distribute_method(
        self,
        method: Callable,
        token: str,
        environment: str,
        df: fugue.AnyDataFrame,
        kwargs: dict,
        schema: str,
        num_partitions: int,
        id_col: str,
        X_df: Optional[fugue.AnyDataFrame] = None,
    ):
        if id_col not in fa.get_column_names(df):
            raise Exception(
                "Distributed environment is meant to forecasts "
                "multiple time series at once. You did not provide "
                "an identifier for each time series."
            )
        engine = make_execution_engine(infer_by=[df])
        if num_partitions is None:
            num_partitions = engine.get_current_parallelism()
        partition = dict(by=id_col, num=num_partitions, algo="coarse")
        if X_df is not None:
            raise Exception(
                "Exogenous variables not supported for "
                "distributed environments yet. "
                "Please rise an issue at https://github.com/Nixtla/nixtla/issues/new "
                "requesting the feature."
            )
        result_df = fa.transform(
            df,
            method,
            params=dict(
                token=token,
                environment=environment,
                kwargs=kwargs,
            ),
            schema=schema,
            engine=engine,
            partition=partition,
            as_fugue=True,
        )
        return fa.get_native_as_df(result_df)

    def forecast(
        self,
        token: str,
        environment: str,
        df: fugue.AnyDataFrame,
        h: int,
        freq: Optional[str] = None,
        id_col: str = "unique_id",
        time_col: str = "ds",
        target_col: str = "y",
        X_df: Optional[fugue.AnyDataFrame] = None,
        level: Optional[List[Union[int, float]]] = None,
        finetune_steps: int = 0,
        clean_ex_first: bool = True,
        validate_token: bool = False,
        add_history: bool = False,
        date_features: Union[bool, List[str]] = False,
        date_features_to_one_hot: Union[bool, List[str]] = True,
        num_partitions: Optional[int] = None,
    ) -> fugue.AnyDataFrame:
        kwargs = dict(
            h=h,
            freq=freq,
            id_col=id_col,
            time_col=time_col,
            target_col=target_col,
            level=level,
            finetune_steps=finetune_steps,
            clean_ex_first=clean_ex_first,
            validate_token=validate_token,
            add_history=add_history,
            date_features=date_features,
            date_features_to_one_hot=date_features_to_one_hot,
        )
        schema = self._get_forecast_schema(
            id_col=id_col, time_col=time_col, level=level
        )
        fcst_df = self._distribute_method(
            method=self._forecast,
            token=token,
            environment=environment,
            df=df,
            kwargs=kwargs,
            schema=schema,
            num_partitions=num_partitions,
            id_col=id_col,
            X_df=X_df,
        )
        return fcst_df

    def detect_anomalies(
        self,
        token: str,
        environment: str,
        df: pd.DataFrame,
        freq: Optional[str] = None,
        id_col: str = "unique_id",
        time_col: str = "ds",
        target_col: str = "y",
        level: Union[int, float] = 99,
        validate_token: bool = False,
        num_partitions: Optional[int] = None,
    ) -> fugue.AnyDataFrame:
        kwargs = dict(
            freq=freq,
            id_col=id_col,
            time_col=time_col,
            target_col=target_col,
            level=level,
            validate_token=validate_token,
        )
        schema = self._get_anomalies_schema(id_col=id_col, time_col=time_col)
        anomalies_df = self._distribute_method(
            method=self._detect_anomalies,
            token=token,
            environment=environment,
            df=df,
            kwargs=kwargs,
            schema=schema,
            num_partitions=num_partitions,
            id_col=id_col,
            X_df=None,
        )
        return anomalies_df

    def _instantiate_timegpt(self, token: str, environment: str):
        from nixtlats.timegpt import _TimeGPT

        timegpt = _TimeGPT(token=token, environment=environment)
        return timegpt

    def _forecast(
        self,
        df: pd.DataFrame,
        token: str,
        environment: str,
        kwargs,
    ) -> pd.DataFrame:
        timegpt = self._instantiate_timegpt(token, environment)
        return timegpt._forecast(df=df, **kwargs)

    def _detect_anomalies(
        self,
        df: pd.DataFrame,
        token: str,
        environment: str,
        kwargs,
    ) -> pd.DataFrame:
        timegpt = self._instantiate_timegpt(token, environment)
        return timegpt._detect_anomalies(df=df, **kwargs)

    @staticmethod
    def _get_forecast_schema(id_col, time_col, level):
        schema = f"{id_col}:string,{time_col}:datetime,TimeGPT:double"
        if level is not None:
            level = sorted(level)
            schema = f'{schema},{",".join([f"TimeGPT-lo-{lv}:double" for lv in reversed(level)])}'
            schema = f'{schema},{",".join([f"TimeGPT-hi-{lv}:double" for lv in level])}'
        return Schema(schema)

    @staticmethod
    def _get_anomalies_schema(id_col, time_col):
        schema = f"{id_col}:string,{time_col}:datetime,anomaly:int"
        return Schema(schema)