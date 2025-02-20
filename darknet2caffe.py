# The caffe module needs to be on the Python path;
#  we'll add it here explicitly.

from __future__ import print_function

caffe_root='/data/project/caffe/'
#os.chdir(caffe_root)
import sys
sys.path.insert(0,caffe_root+'python')
import caffe
import numpy as np
from collections import OrderedDict
from cfg import *
from prototxt import *

def darknet2caffe(cfgfile, weightfile, protofile, caffemodel):
    net_info = cfg2prototxt(cfgfile)
    save_prototxt(net_info , protofile, region=False)
    
    net = caffe.Net(protofile, caffe.TEST)
    params = net.params

    blocks = parse_cfg(cfgfile)

    #Open the weights file
    fp = open(weightfile, "rb")
    
    #The first 4 values are header information 
    # 1. Major version number
    # 2. Minor Version Number
    # 3. Subversion number 
    # 4. IMages seen 
    header = np.fromfile(fp, count=5, dtype=np.int32)
    print(header)
    
    buf = np.fromfile(fp, dtype = np.float32)
    #print(buf)
    
    fp.close()

    layers = []
    layer_id = 1
    start = 0
    for block in blocks:
        if start >= buf.size:
            break

        if block['type'] == 'net':
            continue
        elif block['type'] == 'convolutional':
            batch_normalize = int(block['batch_normalize'])
            if 'name' in block:
                conv_layer_name  = block['name']
                bn_layer_name    = '%s-bn' % block['name']
                scale_layer_name = '%s-scale' % block['name']
            else:
                conv_layer_name  = 'layer%d-conv' % layer_id
                bn_layer_name    = 'layer%d-bn' % layer_id
                scale_layer_name = 'layer%d-scale' % layer_id

            if batch_normalize:
                print("conv_layer_name:",conv_layer_name)
                start = load_conv_bn2caffe(buf, start, params[conv_layer_name], params[bn_layer_name], params[scale_layer_name])
            else:
                print("conv_layer_name:",conv_layer_name)
                start = load_conv2caffe(buf, start, params[conv_layer_name])
            layer_id = layer_id+1
        elif block['type'] == 'connected':
            if 'name' in block:
                fc_layer_name = block['name']
            else:
                fc_layer_name = 'layer%d-fc' % layer_id
            start = load_fc2caffe(buf, start, params[fc_layer_name])
            layer_id = layer_id + 1
        elif block['type'] == 'maxpool':
            layer_id = layer_id + 1
        elif block['type'] == 'avgpool':
            layer_id = layer_id + 1
        elif block['type'] == 'region':
            layer_id = layer_id + 1
        elif block['type'] == 'route':
            layer_id = layer_id + 1
        elif block['type'] == 'shortcut':
            layer_id = layer_id + 1
        elif block['type'] == 'softmax':
            layer_id = layer_id + 1
        elif block['type'] == 'cost':
            layer_id = layer_id + 1
        elif block['type'] == 'upsample':
            layer_id = layer_id + 1
        else:
            print('unknow layer type %s ' % block['type'])
            layer_id = layer_id + 1
    print('save prototxt to %s' % protofile)
    save_prototxt(net_info , protofile, region=True)
    print('save caffemodel to %s' % caffemodel)
    net.save(caffemodel)

def load_conv2caffe(buf, start, conv_param):
    weight = conv_param[0].data
    bias   = conv_param[1].data
    print("start:",start,"conv_weight.size:", weight.size, "conv_weight.shape:", weight.shape, "buflen:", len(buf))
    conv_param[1].data[...] = np.reshape(buf[start:start+bias.size], bias.shape); start = start + bias.size
    conv_param[0].data[...] = np.reshape(buf[start:start+weight.size], weight.shape); start = start + weight.size
    return start

def load_fc2caffe(buf, start, fc_param):
    weight = fc_param[0].data
    bias   = fc_param[1].data
    fc_param[1].data[...] = np.reshape(buf[start:start+bias.size], bias.shape); start = start + bias.size
    fc_param[0].data[...] = np.reshape(buf[start:start+weight.size], weight.shape); start = start + weight.size
    
    return start


def load_conv_bn2caffe(buf, start, conv_param, bn_param, scale_param):
    conv_weight  = conv_param[0].data
    running_mean = bn_param[0].data
    running_var  = bn_param[1].data
    scale_weight = scale_param[0].data
    scale_bias   = scale_param[1].data

    scale_param[1].data[...] = np.reshape(buf[start:start+scale_bias.size], scale_bias.shape);     start = start + scale_bias.size
    scale_param[0].data[...] = np.reshape(buf[start:start+scale_weight.size], scale_weight.shape); start = start + scale_weight.size
    bn_param[0].data[...]    = np.reshape(buf[start:start+running_mean.size], running_mean.shape); start = start + running_mean.size
    bn_param[1].data[...]    = np.reshape(buf[start:start+running_var.size], running_var.shape);   start = start + running_var.size
    bn_param[2].data[...]    = np.array([1.0])
    print("start:",start,"conv_weight.size:", conv_weight.size, "conv_weight.shape:", conv_weight.shape, "buflen:", len(buf))
    conv_param[0].data[...]  = np.reshape(buf[start:start+conv_weight.size], conv_weight.shape);   start = start + conv_weight.size    
    return start

def cfg2prototxt(cfgfile):
    blocks = parse_cfg(cfgfile)

    layers = []
    props  = OrderedDict() 
    bottom = 'data'
    layer_id = 1
    topnames = dict()
    for block in blocks:
        if block['type'] == 'net':
            props['name'] = 'Darkent2Caffe'
            props['input'] = 'data'
            props['input_dim'] = ['1']
            props['input_dim'].append(block['channels'])
            props['input_dim'].append(block['height'])
            props['input_dim'].append(block['width'])
            continue
        elif block['type'] == 'convolutional':
            conv_layer = OrderedDict()
            conv_layer['bottom'] = bottom
            if 'name' in block:
                conv_layer['top']  = block['name']
                conv_layer['name'] = block['name']
            else:
                conv_layer['top']  = 'layer%d-conv' % layer_id
                conv_layer['name'] = 'layer%d-conv' % layer_id
            conv_layer['type'] = 'Convolution'
            convolution_param  = OrderedDict()
            convolution_param['num_output']  = block['filters']
            convolution_param['kernel_size'] = block['size']
            if block['pad'] == '1':
                ksize = int(convolution_param['kernel_size'])
                # if ksize >= 1:
                convolution_param['pad'] = str(int(ksize/2))
                # else:
                #     convolution_param['pad'] = '1'
                # convolution_param['pad'] = block['pad']
            convolution_param['stride']  = block['stride']
            if block['batch_normalize'] == '1':
                convolution_param['bias_term'] = 'false'
            else:
                convolution_param['bias_term'] = 'true'
            conv_layer['convolution_param'] = convolution_param
            layers.append(conv_layer)
            bottom = conv_layer['top']

            if block['batch_normalize'] == '1':
                bn_layer = OrderedDict()
                bn_layer['bottom'] = bottom
                bn_layer['top'] = bottom
                if 'name' in block:
                    bn_layer['name'] = '%s-bn' % block['name']
                else:
                    bn_layer['name'] = 'layer%d-bn' % layer_id
                bn_layer['type'] = 'BatchNorm'
                batch_norm_param = OrderedDict()
                batch_norm_param['use_global_stats'] = 'true'
                bn_layer['batch_norm_param'] = batch_norm_param
                layers.append(bn_layer)

                scale_layer = OrderedDict()
                scale_layer['bottom'] = bottom
                scale_layer['top'] = bottom
                if 'name' in block:
                    scale_layer['name'] = '%s-scale' % block['name']
                else:
                    scale_layer['name'] = 'layer%d-scale' % layer_id
                scale_layer['type'] = 'Scale'
                scale_param = OrderedDict()
                scale_param['bias_term'] = 'true'
                scale_layer['scale_param'] = scale_param
                layers.append(scale_layer)

            if block['activation'] != 'linear':
                relu_layer = OrderedDict()
                relu_layer['bottom'] = bottom
                relu_layer['top'] = bottom
                if 'name' in block:
                    relu_layer['name'] = '%s-act' % block['name']
                else:
                    relu_layer['name'] = 'layer%d-act' % layer_id
                relu_layer['type'] = 'ReLU'
                if block['activation'] == 'leaky':
                    relu_param = OrderedDict()
                    relu_param['negative_slope'] = '0.1'
                    relu_layer['relu_param'] = relu_param
                elif block['activation'] == 'mish':
                    relu_layer['type'] = 'Mish' 
                layers.append(relu_layer)
            topnames[layer_id] = bottom
            layer_id = layer_id+1
        elif block['type'] == 'maxpool':
            max_layer = OrderedDict()
            max_layer['bottom'] = bottom
            if 'name' in block:
                max_layer['top'] = block['name']
                max_layer['name'] = block['name']
            else:
                max_layer['top'] = 'layer%d-maxpool' % layer_id
                max_layer['name'] = 'layer%d-maxpool' % layer_id
            max_layer['type'] = 'Pooling'
            pooling_param = OrderedDict()
            pooling_param['kernel_size'] = block['size']
            pooling_param['stride'] = block['stride']
            # pooling_param['stride'] = block['size']
            pooling_param['pool'] = 'MAX'
            if 'pad' not in block or int(block['pad']) == 1:
                pooling_param['pad'] = str(int((int(block['size'])-1)/2))
            max_layer['pooling_param'] = pooling_param
            layers.append(max_layer)
            bottom = max_layer['top']
            topnames[layer_id] = bottom
            layer_id = layer_id+1
        elif block['type'] == 'avgpool':
            avg_layer = OrderedDict()
            avg_layer['bottom'] = bottom
            if 'name' in block:
                avg_layer['top'] = block['name']
                avg_layer['name'] = block['name']
            else:
                avg_layer['top'] = 'layer%d-avgpool' % layer_id
                avg_layer['name'] = 'layer%d-avgpool' % layer_id
            avg_layer['type'] = 'Pooling'
            pooling_param = OrderedDict()
            pooling_param['kernel_size'] = 7
            pooling_param['stride'] = 1
            pooling_param['pool'] = 'AVE'
            avg_layer['pooling_param'] = pooling_param
            layers.append(avg_layer)
            bottom = avg_layer['top']
            topnames[layer_id] = bottom
            layer_id = layer_id+1
        elif block['type'] == 'region':
            region_layer = OrderedDict()
            region_layer['name'] = 'region1'
            region_layer['type'] = 'Region'                         
            region_layer['bottom'] = bottom
            region_layer['top'] = 'region1' 
            region_param = OrderedDict()
            region_param['classes'] = block['classes']
            region_param['coords'] = block['coords']
            region_param['boxes_of_each_grid'] = 5
            region_param['softmax'] = 'true'
            region_layer['region_param'] = region_param
            layers.append(region_layer)
            bottom = region_layer['top']
            topnames[layer_id] = bottom
            layer_id = layer_id + 1
        elif block['type'] == 'route':
            route_layer = OrderedDict()
            layer_name = str(block['layers']).split(',')
            print("layers:", layer_name, " layer_id:", layer_id)
            bottom_layer_size = len(str(block['layers']).split(','))
            # print(bottom_layer_size)
            if(1 == bottom_layer_size):
                prev_layer_id = int(block['layers'])
                if prev_layer_id < 0:
                    prev_layer_id += layer_id
                else:
                    prev_layer_id += 1
                print("topnames:",topnames, " need:", prev_layer_id)
                bottom = topnames[prev_layer_id]
                #topnames[layer_id] = bottom
                route_layer['bottom'] = bottom
            elif(2 == bottom_layer_size):
                prev_layer_id1 = int(layer_name[0])
                if prev_layer_id1 < 0:
                    prev_layer_id1 += layer_id
                else:
                    prev_layer_id1 += 1
                #print(prev_layer_id1)
                prev_layer_id2 = int(layer_name[1])
                if prev_layer_id2 < 0:
                    prev_layer_id2 += layer_id
                else:
                    prev_layer_id2 += 1
                print(topnames, " need:", prev_layer_id1, prev_layer_id2)
                bottom1 = topnames[prev_layer_id1]
                bottom2 = topnames[prev_layer_id2]
                route_layer['bottom'] = [bottom1, bottom2]
            else:
                prev_layer_ids = [int(x) for x in layer_name]
                for ii in range(len(prev_layer_ids)):
                    if prev_layer_ids[ii] < 0:
                        prev_layer_ids[ii] += layer_id
                    else:
                        prev_layer_ids[ii] += 1
                
                print(topnames, " need:", prev_layer_ids)
                route_layer['bottom'] = [topnames[layer_id] for layer_id in prev_layer_ids]

            if 'name' in block:
                route_layer['top'] = block['name']
                route_layer['name'] = block['name']
            else:
                route_layer['top'] = 'layer%d-route' % layer_id
                route_layer['name'] = 'layer%d-route' % layer_id
            route_layer['type'] = 'Concat'
            print(route_layer)
            layers.append(route_layer)
            bottom = route_layer['top']
            print(layer_id)
            if 'groups' in block:
                slice_layer = OrderedDict()
                slice_layer["name"] = bottom+"_slice"
                slice_layer["type"] = "Slice"
                slice_layer["bottom"] = bottom

                spliceto = int(block['groups'])
                bottomidx = int(block['group_id'])
                silencidx = (1-bottomidx)

                slice_param = OrderedDict()
                if spliceto == 2:
                    slice_param['slice_dim'] = 1
                
                scale_layer['slice_param'] = slice_param
                
                slice_layer["top"] = [bottom+"_slice0", bottom+"_slice1"]
                bottom = slice_layer["top"][bottomidx]

                print(slice_layer)
                layers.append(slice_layer)
                print(layer_id)

                
                silenc_layer = OrderedDict()
                bottom_silence = slice_layer["top"][silencidx]
                silenc_layer["name"] = bottom_silence+"_silence"
                silenc_layer["type"] = "Silence"
                silenc_layer["bottom"] = bottom_silence
                layers.append(silenc_layer)

            topnames[layer_id] = bottom
            layer_id = layer_id + 1
        elif block['type'] == 'upsample':
            upsample_layer = OrderedDict()
            print(block['stride'])
            upsample_layer['bottom'] = bottom
            if 'name' in block:
                upsample_layer['top'] = block['name']
                upsample_layer['name'] = block['name']
            else:
                upsample_layer['top'] = 'layer%d-upsample' % layer_id
                upsample_layer['name'] = 'layer%d-upsample' % layer_id
            upsample_layer['type'] = 'Upsample'
            upsample_param = OrderedDict()
            upsample_param['scale'] = block['stride']
            #upsample_param['nearestneighbor_mode'] = "true"
            upsample_layer['upsample_param'] = upsample_param
            print(upsample_layer)
            layers.append(upsample_layer)
            bottom = upsample_layer['top']
            print('upsample:',layer_id)
            topnames[layer_id] = bottom
            layer_id = layer_id + 1
        elif block['type'] == 'shortcut':
            prev_layer_id1 = layer_id + int(block['from'])
            prev_layer_id2 = layer_id - 1
            bottom1 = topnames[prev_layer_id1]
            bottom2= topnames[prev_layer_id2]
            shortcut_layer = OrderedDict()
            shortcut_layer['bottom'] = [bottom1, bottom2]
            if 'name' in block:
                shortcut_layer['top'] = block['name']
                shortcut_layer['name'] = block['name']
            else:
                shortcut_layer['top'] = 'layer%d-shortcut' % layer_id
                shortcut_layer['name'] = 'layer%d-shortcut' % layer_id
            shortcut_layer['type'] = 'Eltwise'
            eltwise_param = OrderedDict()
            eltwise_param['operation'] = 'SUM'
            shortcut_layer['eltwise_param'] = eltwise_param
            layers.append(shortcut_layer)
            bottom = shortcut_layer['top']
           
            if block['activation'] != 'linear':
                relu_layer = OrderedDict()
                relu_layer['bottom'] = bottom
                relu_layer['top'] = bottom
                if 'name' in block:
                    relu_layer['name'] = '%s-act' % block['name']
                else:
                    relu_layer['name'] = 'layer%d-act' % layer_id
                relu_layer['type'] = 'ReLU'
                if block['activation'] == 'leaky':
                    relu_param = OrderedDict()
                    relu_param['negative_slope'] = '0.1'
                    relu_layer['relu_param'] = relu_param
                layers.append(relu_layer)
            topnames[layer_id] = bottom
            layer_id = layer_id + 1           
        elif block['type'] == 'connected':
            fc_layer = OrderedDict()
            fc_layer['bottom'] = bottom
            if 'name' in block:
                fc_layer['top'] = block['name']
                fc_layer['name'] = block['name']
            else:
                fc_layer['top'] = 'layer%d-fc' % layer_id
                fc_layer['name'] = 'layer%d-fc' % layer_id
            fc_layer['type'] = 'InnerProduct'
            fc_param = OrderedDict()
            fc_param['num_output'] = int(block['output'])
            fc_layer['inner_product_param'] = fc_param
            layers.append(fc_layer)
            bottom = fc_layer['top']
            
            if block['activation'] != 'linear':
                relu_layer = OrderedDict()
                relu_layer['bottom'] = bottom
                relu_layer['top'] = bottom
                if 'name' in block:
                    relu_layer['name'] = '%s-act' % block['name']
                else:
                    relu_layer['name'] = 'layer%d-act' % layer_id
                relu_layer['type'] = 'ReLU'
                if block['activation'] == 'leaky':
                    relu_param = OrderedDict()
                    relu_param['negative_slope'] = '0.1'
                    relu_layer['relu_param'] = relu_param
                layers.append(relu_layer)
            topnames[layer_id] = bottom
            layer_id = layer_id+1
        else:
            print('unknow layer type %s ' % block['type'])
            topnames[layer_id] = bottom
            layer_id = layer_id + 1

    net_info = OrderedDict()
    net_info['props'] = props
    net_info['layers'] = layers
    return net_info

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 5:
        print('try:')
        print('python darknet2caffe.py tiny-yolo-voc.cfg tiny-yolo-voc.weights tiny-yolo-voc.prototxt tiny-yolo-voc.caffemodel')
        print('')
        print('please add name field for each block to avoid generated name')
        exit()

    cfgfile = sys.argv[1]
    # net_info = cfg2prototxt(cfgfile)
    # print_prototxt(net_info)
    # save_prototxt(net_info, 'tmp.prototxt')
    weightfile = sys.argv[2]
    protofile  = sys.argv[3]
    caffemodel = sys.argv[4]
    darknet2caffe(cfgfile, weightfile, protofile, caffemodel)
