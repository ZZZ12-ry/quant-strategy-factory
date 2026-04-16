"""
深度学习模型 - LSTM / GRU / Transformer
用于量化预测的时序深度学习模型
参考：Qlib Deep Learning, Time Series Transformers
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime


class DeepLearningModel:
    """深度学习模型基类"""
    
    def __init__(self, model_type: str = "lstm"):
        """
        初始化深度学习模型
        
        Args:
            model_type: 模型类型 (lstm/gru/transformer/cnn_lstm)
        """
        self.model_type = model_type
        self.model = None
        self.history = None
        self.is_pytorch = False
        self.is_tensorflow = False
    
    def build_lstm(
        self,
        input_shape: Tuple[int, int],
        lstm_units: List[int] = [64, 32],
        dropout_rate: float = 0.2,
        dense_units: List[int] = [32],
        output_units: int = 1,
        activation: str = "relu"
    ) -> Any:
        """
        构建 LSTM 模型
        
        Args:
            input_shape: 输入形状 (time_steps, features)
            lstm_units: LSTM 层单元数列表
            dropout_rate: Dropout 比率
            dense_units: 全连接层单元数列表
            output_units: 输出单元数
            activation: 激活函数
        
        Returns:
            模型实例
        """
        try:
            import torch
            import torch.nn as nn
            self.is_pytorch = True
        except ImportError:
            try:
                import tensorflow as tf
                from tensorflow import keras
                self.is_tensorflow = True
                return self._build_lstm_tf(input_shape, lstm_units, dropout_rate, dense_units, output_units, activation)
            except ImportError:
                raise ImportError("Please install PyTorch or TensorFlow: pip install torch tensorflow")
        
        # PyTorch 实现
        class LSTMNet(torch.nn.Module):
            def __init__(self, input_size, lstm_units, dropout_rate, dense_units, output_units):
                super(LSTMNet, self).__init__()
                
                self.lstm_layers = nn.ModuleList()
                prev_size = input_size
                
                for i, units in enumerate(lstm_units):
                    self.lstm_layers.append(nn.LSTM(prev_size, units, batch_first=True, dropout=dropout_rate if i > 0 else 0))
                    prev_size = units
                
                self.dropout = nn.Dropout(dropout_rate)
                
                self.dense_layers = nn.ModuleList()
                for units in dense_units:
                    self.dense_layers.append(nn.Linear(prev_size, units))
                    self.dense_layers.append(nn.ReLU())
                    self.dense_layers.append(nn.Dropout(dropout_rate))
                    prev_size = units
                
                self.output = nn.Linear(prev_size, output_units)
            
            def forward(self, x):
                for lstm in self.lstm_layers:
                    x, _ = lstm(x)
                
                x = x[:, -1, :]  # 取最后一个时间步
                x = self.dropout(x)
                
                for layer in self.dense_layers:
                    x = layer(x)
                
                return self.output(x)
        
        input_size = input_shape[1]
        model = LSTMNet(input_size, lstm_units, dropout_rate, dense_units, output_units)
        
        self.model = model
        return model
    
    def _build_lstm_tf(
        self,
        input_shape: Tuple[int, int],
        lstm_units: List[int],
        dropout_rate: float,
        dense_units: List[int],
        output_units: int,
        activation: str
    ) -> Any:
        """TensorFlow LSTM 模型"""
        import tensorflow as tf
        from tensorflow import keras
        
        model = keras.Sequential()
        
        # LSTM 层
        for i, units in enumerate(lstm_units):
            return_sequences = i < len(lstm_units) - 1
            model.add(keras.layers.LSTM(units, return_sequences=return_sequences, input_shape=input_shape))
            if return_sequences:
                model.add(keras.layers.Dropout(dropout_rate))
        
        # 全连接层
        for units in dense_units:
            model.add(keras.layers.Dense(units, activation=activation))
            model.add(keras.layers.Dropout(dropout_rate))
        
        # 输出层
        model.add(keras.layers.Dense(output_units))
        
        self.model = model
        return model
    
    def build_gru(
        self,
        input_shape: Tuple[int, int],
        gru_units: List[int] = [64, 32],
        dropout_rate: float = 0.2,
        dense_units: List[int] = [32],
        output_units: int = 1
    ) -> Any:
        """
        构建 GRU 模型（比 LSTM 更快）
        
        Args:
            input_shape: 输入形状 (time_steps, features)
            gru_units: GRU 层单元数列表
            dropout_rate: Dropout 比率
            dense_units: 全连接层单元数列表
            output_units: 输出单元数
        
        Returns:
            模型实例
        """
        try:
            import torch
            import torch.nn as nn
            self.is_pytorch = True
        except ImportError:
            try:
                import tensorflow as tf
                from tensorflow import keras
                self.is_tensorflow = True
                return self._build_gru_tf(input_shape, gru_units, dropout_rate, dense_units, output_units)
            except ImportError:
                raise ImportError("Please install PyTorch or TensorFlow")
        
        # PyTorch 实现
        class GRUNet(torch.nn.Module):
            def __init__(self, input_size, gru_units, dropout_rate, dense_units, output_units):
                super(GRUNet, self).__init__()
                
                self.gru_layers = nn.ModuleList()
                prev_size = input_size
                
                for i, units in enumerate(gru_units):
                    self.gru_layers.append(nn.GRU(prev_size, units, batch_first=True, dropout=dropout_rate if i > 0 else 0))
                    prev_size = units
                
                self.dropout = nn.Dropout(dropout_rate)
                
                self.dense_layers = nn.ModuleList()
                for units in dense_units:
                    self.dense_layers.append(nn.Linear(prev_size, units))
                    self.dense_layers.append(nn.ReLU())
                    self.dense_layers.append(nn.Dropout(dropout_rate))
                    prev_size = units
                
                self.output = nn.Linear(prev_size, output_units)
            
            def forward(self, x):
                for gru in self.gru_layers:
                    x, _ = gru(x)
                
                x = x[:, -1, :]
                x = self.dropout(x)
                
                for layer in self.dense_layers:
                    x = layer(x)
                
                return self.output(x)
        
        input_size = input_shape[1]
        model = GRUNet(input_size, gru_units, dropout_rate, dense_units, output_units)
        
        self.model = model
        return model
    
    def _build_gru_tf(
        self,
        input_shape: Tuple[int, int],
        gru_units: List[int],
        dropout_rate: float,
        dense_units: List[int],
        output_units: int
    ) -> Any:
        """TensorFlow GRU 模型"""
        import tensorflow as tf
        from tensorflow import keras
        
        model = keras.Sequential()
        
        for i, units in enumerate(gru_units):
            return_sequences = i < len(gru_units) - 1
            model.add(keras.layers.GRU(units, return_sequences=return_sequences, input_shape=input_shape))
            if return_sequences:
                model.add(keras.layers.Dropout(dropout_rate))
        
        for units in dense_units:
            model.add(keras.layers.Dense(units, activation='relu'))
            model.add(keras.layers.Dropout(dropout_rate))
        
        model.add(keras.layers.Dense(output_units))
        
        self.model = model
        return model
    
    def build_transformer(
        self,
        input_shape: Tuple[int, int],
        d_model: int = 64,
        n_heads: int = 4,
        n_layers: int = 3,
        d_ff: int = 128,
        dropout_rate: float = 0.1,
        max_len: int = 100
    ) -> Any:
        """
        构建 Transformer 编码器模型
        
        Args:
            input_shape: 输入形状 (time_steps, features)
            d_model: 模型维度
            n_heads: 注意力头数
            n_layers: 编码器层数
            d_ff: 前馈网络维度
            dropout_rate: Dropout 比率
            max_len: 最大序列长度
        
        Returns:
            模型实例
        """
        try:
            import torch
            import torch.nn as nn
            self.is_pytorch = True
        except ImportError:
            try:
                import tensorflow as tf
                from tensorflow import keras
                self.is_tensorflow = True
                return self._build_transformer_tf(input_shape, d_model, n_heads, n_layers, d_ff, dropout_rate)
            except ImportError:
                raise ImportError("Please install PyTorch or TensorFlow")
        
        # PyTorch Transformer
        class PositionalEncoding(nn.Module):
            def __init__(self, d_model, max_len=100, dropout=0.1):
                super(PositionalEncoding, self).__init__()
                self.dropout = nn.Dropout(p=dropout)
                
                pe = torch.zeros(max_len, d_model)
                position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
                div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
                pe[:, 0::2] = torch.sin(position * div_term)
                pe[:, 1::2] = torch.cos(position * div_term)
                pe = pe.unsqueeze(0)
                self.register_buffer('pe', pe)
            
            def forward(self, x):
                x = x + self.pe[:, :x.size(1), :]
                return self.dropout(x)
        
        class TransformerNet(nn.Module):
            def __init__(self, input_size, d_model, n_heads, n_layers, d_ff, dropout):
                super(TransformerNet, self).__init__()
                
                self.input_projection = nn.Linear(input_size, d_model)
                self.pos_encoder = PositionalEncoding(d_model, max_len=max_len, dropout=dropout)
                
                encoder_layer = nn.TransformerEncoderLayer(
                    d_model=d_model,
                    nhead=n_heads,
                    dim_feedforward=d_ff,
                    dropout=dropout,
                    batch_first=True
                )
                self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
                
                self.output = nn.Linear(d_model, 1)
            
            def forward(self, x):
                x = self.input_projection(x)
                x = self.pos_encoder(x)
                x = self.transformer_encoder(x)
                x = x[:, -1, :]  # 取最后一个时间步
                return self.output(x)
        
        input_size = input_shape[1]
        model = TransformerNet(input_size, d_model, n_heads, n_layers, d_ff, dropout_rate)
        
        self.model = model
        return model
    
    def _build_transformer_tf(
        self,
        input_shape: Tuple[int, int],
        d_model: int,
        n_heads: int,
        n_layers: int,
        d_ff: int,
        dropout_rate: float
    ) -> Any:
        """TensorFlow Transformer 模型"""
        import tensorflow as tf
        from tensorflow import keras
        
        inputs = keras.Input(shape=input_shape)
        
        # 投影层
        x = keras.layers.Dense(d_model)(inputs)
        
        # 位置编码（简化）
        # 使用 Transformer Encoder
        for _ in range(n_layers):
            attention_output = keras.layers.MultiHeadAttention(num_heads=n_heads, key_dim=d_model // n_heads)(x, x)
            attention_output = keras.layers.Dropout(dropout_rate)(attention_output)
            x = keras.layers.LayerNormalization(epsilon=1e-6)(x + attention_output)
            
            ffn = keras.Sequential([
                keras.layers.Dense(d_ff, activation="relu"),
                keras.layers.Dense(d_model)
            ])
            ffn_output = ffn(x)
            ffn_output = keras.layers.Dropout(dropout_rate)(ffn_output)
            x = keras.layers.LayerNormalization(epsilon=1e-6)(x + ffn_output)
        
        # 全局平均池化
        x = keras.layers.GlobalAveragePooling1D()(x)
        x = keras.layers.Dropout(dropout_rate)(x)
        outputs = keras.layers.Dense(1)(x)
        
        model = keras.Model(inputs=inputs, outputs=outputs)
        
        self.model = model
        return model
    
    def prepare_sequences(
        self,
        data: pd.DataFrame,
        target_col: str,
        feature_cols: List[str],
        lookback: int = 60,
        horizon: int = 5,
        train_ratio: float = 0.7
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        准备时序数据
        
        Args:
            data: DataFrame 数据
            target_col: 目标列
            feature_cols: 特征列
            lookback: 回溯窗口长度
            horizon: 预测 horizon
            train_ratio: 训练集比例
        
        Returns:
            (X_train, y_train, X_test, y_test)
        """
        # 提取特征和目标
        features = data[feature_cols].values
        target = data[target_col].values
        
        # 创建序列
        X, y = [], []
        
        for i in range(lookback, len(features) - horizon):
            X.append(features[i-lookback:i])
            y.append(target[i])  # 预测当前价格
        
        X = np.array(X)
        y = np.array(y)
        
        # 划分训练测试集
        split_idx = int(len(X) * train_ratio)
        
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        return X_train, y_train, X_test, y_test
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray = None,
        y_val: np.ndarray = None,
        epochs: int = 50,
        batch_size: int = 32,
        learning_rate: float = 0.001,
        early_stopping_patience: int = 10
    ) -> Dict[str, List[float]]:
        """
        训练深度学习模型
        
        Args:
            X_train: 训练特征 (samples, time_steps, features)
            y_train: 训练标签
            X_val: 验证特征
            y_val: 验证标签
            epochs: 训练轮数
            batch_size: 批次大小
            learning_rate: 学习率
            early_stopping_patience: 早停耐心值
        
        Returns:
            训练历史
        """
        if self.model is None:
            raise ValueError("Model not built. Call build_* first.")
        
        history = {'loss': [], 'val_loss': []}
        
        if self.is_pytorch:
            return self._train_pytorch(X_train, y_train, X_val, y_val, epochs, batch_size, learning_rate, early_stopping_patience, history)
        elif self.is_tensorflow:
            return self._train_tensorflow(X_train, y_train, X_val, y_val, epochs, batch_size, learning_rate, early_stopping_patience, history)
        else:
            raise ValueError("Unknown framework")
    
    def _train_pytorch(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        epochs: int,
        batch_size: int,
        learning_rate: float,
        patience: int,
        history: Dict
    ) -> Dict:
        """PyTorch 训练"""
        import torch
        import torch.nn as nn
        import torch.optim as optim
        from torch.utils.data import TensorDataset, DataLoader
        
        # 转换为 Tensor
        X_train_t = torch.FloatTensor(X_train)
        y_train_t = torch.FloatTensor(y_train).unsqueeze(1)
        
        X_val_t = torch.FloatTensor(X_val) if X_val is not None else None
        y_val_t = torch.FloatTensor(y_val).unsqueeze(1) if y_val is not None else None
        
        # 创建 DataLoader
        train_dataset = TensorDataset(X_train_t, y_train_t)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        
        # 损失函数和优化器
        criterion = nn.MSELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)
        
        best_val_loss = float('inf')
        patience_counter = 0
        
        for epoch in range(epochs):
            # 训练
            self.model.train()
            train_loss = 0.0
            
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()
            
            train_loss /= len(train_loader)
            history['loss'].append(train_loss)
            
            # 验证
            if X_val_t is not None:
                self.model.eval()
                with torch.no_grad():
                    val_outputs = self.model(X_val_t)
                    val_loss = criterion(val_outputs, y_val_t).item()
                history['val_loss'].append(val_loss)
                
                scheduler.step(val_loss)
                
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1
                
                if (epoch + 1) % 10 == 0:
                    print(f"Epoch {epoch+1}/{epochs} - Train Loss: {train_loss:.6f} - Val Loss: {val_loss:.6f}")
                
                # 早停
                if patience_counter >= patience:
                    print(f"Early stopping at epoch {epoch+1}")
                    break
            else:
                if (epoch + 1) % 10 == 0:
                    print(f"Epoch {epoch+1}/{epochs} - Train Loss: {train_loss:.6f}")
        
        self.history = history
        return history
    
    def _train_tensorflow(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        epochs: int,
        batch_size: int,
        learning_rate: float,
        patience: int,
        history: Dict
    ) -> Dict:
        """TensorFlow 训练"""
        import tensorflow as tf
        from tensorflow import keras
        
        # 编译模型
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
            loss='mse',
            metrics=['mae']
        )
        
        # 回调
        callbacks = [
            keras.callbacks.EarlyStopping(monitor='val_loss', patience=patience, restore_best_weights=True),
            keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6)
        ]
        
        # 训练
        hist = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val) if X_val is not None else None,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            verbose=1
        )
        
        self.history = hist.history
        return self.history
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测"""
        if self.model is None:
            raise ValueError("Model not trained")
        
        if self.is_pytorch:
            import torch
            self.model.eval()
            with torch.no_grad():
                X_t = torch.FloatTensor(X)
                pred = self.model(X_t).numpy()
            return pred.flatten()
        elif self.is_tensorflow:
            return self.model.predict(X, verbose=0).flatten()
        else:
            raise ValueError("Unknown framework")
    
    def save_model(self, filepath: str):
        """保存模型"""
        import pickle
        
        if self.is_tensorflow:
            self.model.save(filepath + '.h5')
        elif self.is_pytorch:
            import torch
            torch.save({
                'model_state_dict': self.model.state_dict(),
                'model_type': self.model_type
            }, filepath + '.pth')
        
        # 保存元数据
        with open(filepath + '.meta', 'wb') as f:
            pickle.dump({
                'model_type': self.model_type,
                'is_pytorch': self.is_pytorch,
                'is_tensorflow': self.is_tensorflow
            }, f)
    
    def load_model(self, filepath: str):
        """加载模型"""
        import pickle
        
        with open(filepath + '.meta', 'rb') as f:
            meta = pickle.load(f)
        
        self.model_type = meta['model_type']
        self.is_pytorch = meta['is_pytorch']
        self.is_tensorflow = meta['is_tensorflow']
        
        if self.is_tensorflow:
            import tensorflow as tf
            from tensorflow import keras
            self.model = keras.models.load_model(filepath + '.h5')
        elif self.is_pytorch:
            import torch
            import torch.nn as nn
            
            # 需要重新构建模型结构
            checkpoint = torch.load(filepath + '.pth')
            # 这里需要根据 model_type 重建模型
            # 简化处理，实际需要保存模型结构参数
            print("⚠️  PyTorch 模型加载需要重建模型结构")


class DeepLearningPredictor:
    """深度学习预测器 - 用于策略集成"""
    
    def __init__(self, model: DeepLearningModel = None):
        self.model = model
        self.feature_buffer = []
        self.max_len = 100
    
    def update_buffer(self, features: Dict[str, float]):
        """更新特征缓冲区"""
        self.feature_buffer.append(features)
        if len(self.feature_buffer) > self.max_len:
            self.feature_buffer = self.feature_buffer[-self.max_len:]
    
    def prepare_input(self, lookback: int = 60) -> Optional[np.ndarray]:
        """准备模型输入"""
        if len(self.feature_buffer) < lookback:
            return None
        
        # 转换为数组
        feature_names = list(self.feature_buffer[-1].keys())
        X = np.zeros((1, lookback, len(feature_names)))
        
        for t in range(lookback):
            for f_idx, fname in enumerate(feature_names):
                X[0, t, f_idx] = self.feature_buffer[-(lookback - t)][fname]
        
        return X
    
    def predict(self, lookback: int = 60) -> Optional[float]:
        """预测"""
        if self.model is None:
            return None
        
        X = self.prepare_input(lookback)
        if X is None:
            return None
        
        pred = self.model.predict(X)
        return pred[0]


# 便捷函数
def create_lstm_model(input_shape, **kwargs):
    """快速创建 LSTM 模型"""
    model = DeepLearningModel(model_type="lstm")
    model.build_lstm(input_shape, **kwargs)
    return model

def create_gru_model(input_shape, **kwargs):
    """快速创建 GRU 模型"""
    model = DeepLearningModel(model_type="gru")
    model.build_gru(input_shape, **kwargs)
    return model

def create_transformer_model(input_shape, **kwargs):
    """快速创建 Transformer 模型"""
    model = DeepLearningModel(model_type="transformer")
    model.build_transformer(input_shape, **kwargs)
    return model
