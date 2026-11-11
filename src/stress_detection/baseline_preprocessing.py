"""Import-stable fold-local preprocessing for portable local model artifacts."""

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler


class FoldPreprocessor:
    """Train-only median imputation/scaling; drop only train-all-missing columns."""

    def fit(self,x):
        x=np.asarray(x,dtype=float)
        if x.ndim!=2 or len(x)==0 or np.isinf(x).any():
            raise ValueError('Invalid training matrix')
        self.keep_=~np.isnan(x).all(axis=0)
        self.n_features_in_=x.shape[1]
        self.imputer_=self.scaler_=None
        if self.keep_.any():
            self.imputer_=SimpleImputer(strategy='median',add_indicator=False)
            imputed=self.imputer_.fit_transform(x[:,self.keep_])
            self.scaler_=StandardScaler().fit(imputed)
        return self

    def transform(self,x):
        x=np.asarray(x,dtype=float)
        if x.ndim!=2 or x.shape[1]!=self.n_features_in_ or np.isinf(x).any():
            raise ValueError('Invalid evaluation matrix')
        if not self.keep_.any():
            return np.zeros((len(x),1))
        return self.scaler_.transform(self.imputer_.transform(x[:,self.keep_]))

    def snapshot(self,columns):
        return {'requested_columns':columns,'retained_columns':[c for c,k in zip(columns,self.keep_) if k],
            'training_all_missing_columns':[c for c,k in zip(columns,self.keep_) if not k],
            'median':self.imputer_.statistics_.tolist() if self.imputer_ else [],
            'scaler_mean':self.scaler_.mean_.tolist() if self.scaler_ else [],
            'scaler_scale':self.scaler_.scale_.tolist() if self.scaler_ else [],
            'scaler_variance':self.scaler_.var_.tolist() if self.scaler_ else []}
