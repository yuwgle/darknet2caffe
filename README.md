<!--
 * @Author: le
-->
# Darknet2Caffe
DarkNet下训练的yolo的`.cfg`文件和`.weights`文件转换为Caffe的`.prototxt`文件和`.caffemodel`文件。
现已支持 yolov4_tiny、 yolov4_leaky、 yolov4_mish。 还不支持 激活函数为relu的cfg，因为那不是正经的relu，等我有时间再看看。

### Todo

 - [ ] darknet的relu激活层


### 根目录执行命令：
```

python darknet2caffe.py yolov4_tiny.cfg yolov4_tiny.weights yolov4_tiny.prototxt yolov4_tiny.caffemodel

python darknet2caffe.py yolov4_leaky.cfg yolov4_leaky.weights yolov4_leaky.prototxt yolov4_leaky.caffemodel

```

其中：

1. `yolov4_leaky.cfg` --------- yolov4模型结构文件

2. `yolov4_leaky.weights` ----- yolov4训练好的模型权重文件

3. `yolov4_leaky.prototxt` ---- 待生成的Caffe框架下的模型结构文件

4. `yolov4_leaky.caffemodel` -- 待生成的Caffe框架下的模型权重文件


注：

0. yolo的模型结构和权重可以去 darknet仓库或者官网下载。
 https://github.com/AlexeyAB/darknet/wiki/YOLOv4-model-zoo 
 https://pjreddie.com/darknet/yolo/

1. 修改`darknet2caffe.py`中的Caffe路径（路径为Caffe的根目录，从官方GitHub下载并正常安装，可参考：https://blog.csdn.net/lwplwf/article/details/82415620）

2. 修改`yolov4_leaky.prototxt`文件（和Caffe下region层的实现有关）

将第一层
```
input: "data"
input_dim: 1
input_dim: 3
input_dim: 416
input_dim: 416
```

修改为：

```
layer {
  name: "data"
  type: "Input"
  top: "data"
  input_param { shape: { dim: 1 dim: 3 dim: 416 dim: 416 } }
}

```

# Requirements
  
  Python > 3.5

  Caffe

  Pytorch >= 0.40
# Add Caffe Layers
1. Copy `caffe_layers/mish_layer/mish_layer.hpp,caffe_layers/upsample_layer/upsample_layer.hpp` into `include/caffe/layers/`.
2. Copy `caffe_layers/mish_layer/mish_layer.cpp mish_layer.cu,caffe_layers/upsample_layer/upsample_layer.cpp upsample_layer.cu` into `src/caffe/layers/`.
3. Copy `caffe_layers/pooling_layer/pooling_layer.cpp` into `src/caffe/layers/`.Note:only work for yolov3-tiny,use with caution.
4. Add below code into `src/caffe/proto/caffe.proto`.

```
// LayerParameter next available layer-specific ID: 147 (last added: recurrent_param)
message LayerParameter {
  optional TileParameter tile_param = 138;
  optional VideoDataParameter video_data_param = 207;
  optional WindowDataParameter window_data_param = 129;
++optional UpsampleParameter upsample_param = 149; //added by chen for Yolov3, make sure this id 149 not the same as before.
++optional MishParameter mish_param = 150; //added by chen for yolov4,make sure this id 150 not the same as before.
}

// added by chen for YoloV3
++message UpsampleParameter{
++  optional int32 scale = 1 [default = 1];
++}

// Message that stores parameters used by MishLayer
++message MishParameter {
++  enum Engine {
++    DEFAULT = 0;
++    CAFFE = 1;
++    CUDNN = 2;
++  }
++  optional Engine engine = 2 [default = DEFAULT];
++}
```
5.remake caffe.

# Demo
  $ python cfg[in] weights[in] prototxt[out] caffemodel[out]
  
  Example
```
python cfg/yolov4.cfg weights/yolov4.weights prototxt/yolov4.prototxt caffemodel/yolov4.caffemodel
```
  partial log as below.
```
I0522 10:19:19.015708 25251 net.cpp:228] layer1-act does not need backward computation.
I0522 10:19:19.015712 25251 net.cpp:228] layer1-scale does not need backward computation.
I0522 10:19:19.015714 25251 net.cpp:228] layer1-bn does not need backward computation.
I0522 10:19:19.015718 25251 net.cpp:228] layer1-conv does not need backward computation.
I0522 10:19:19.015722 25251 net.cpp:228] input does not need backward computation.
I0522 10:19:19.015725 25251 net.cpp:270] This network produces output layer139-conv
I0522 10:19:19.015731 25251 net.cpp:270] This network produces output layer150-conv
I0522 10:19:19.015736 25251 net.cpp:270] This network produces output layer161-conv
I0522 10:19:19.015911 25251 net.cpp:283] Network initialization done.
unknow layer type yolo 
unknow layer type yolo 
save prototxt to prototxt/yolov4.prototxt
save caffemodel to caffemodel/yolov4.caffemodel

```

### Reference：
> https://github.com/ChenYingpeng/darknet2caffe

> https://github.com/marvis/pytorch-caffe-darknet-convert

> https://github.com/lwplw/caffe_yolov2
