from . import classification
from .segmentation import *
from torchvision import models as torch_models
from torchvision.models.inception import InceptionAux
import torch.nn as nn
import os

def get_model(type, model_name, num_classes, input_size, pretrained=True):
    '''
    :param type: str
        one of {'classification', 'segmentation'}
    :param model_name: str
        name of the model. By convention (for classification models) lowercase names represent pretrained model variants while Uppercase do not.
    :param num_classes: int
        number of classes to initialize with (this will replace the last classification layer or set the number of segmented classes)
    :param input_size: (int,int)
        Segmentation-only param. What size of input the network will accept e.g. (256, 256), (512, 512)
    :param pretrained: bool
        whether to load the default pretrained version of the model
        NOTE! NOTE! For classification, the lowercase model names are the pretrained variants while the Uppercase model names are not.
        It is IN ERROR to specify an Uppercase model name variant with pretrained=True but one can specify a lowercase model variant with pretrained=False
        (default: True)
    :return model
    '''
    if model_name not in get_supported_models(type) and not model_name.startswith('TEST'):
        raise ValueError('The supplied model name: {} was not found in the list of acceptable model names.'
                         ' Use get_supported_models() to obtain a list of supported models.')

    print("INFO: Loading Model:   --   " + model_name + "  with number of classes: " + str(num_classes))
    
    if type == 'classification':

        # 1. Load model (pretrained or vanilla)
        fc_name = 'last_linear'  # most common name of the last layer (to be replaced)
        if model_name in torch_models.__dict__:
            print('INFO: Loading a pretrained?: {}   model: {}'.format(pretrained, model_name))
            model = torch_models.__dict__[model_name](pretrained=pretrained)  # find a model included in the torchvision package
            if 'densenet' in model_name:    # apparently densenet is special..
                fc_name = 'classifier'  # the name of the last layer to be replaced in torchvision models
            else:
                fc_name = 'fc'  # the name of the last layer to be replaced in torchvision models
        else:
            if pretrained:
                print('INFO: Loading a pretrained model: {}'.format(model_name))
                if 'dpn' in model_name:
                    model = classification.__dict__[model_name](pretrained=True)  # find a model included in the wick classification package
                elif 'inception' in model_name or 'nasnet' in model_name or 'polynet' in model_name or 'resnext' in model_name\
                        or 'se_resnet' in model_name or 'xception' in model_name:
                    model = classification.__dict__[model_name](pretrained='imagenet')
            else:
                print('INFO: Loading a vanilla model: {}'.format(model_name))
                model = classification.__dict__[model_name](pretrained=None)  # pretrained must be set to None for the extra models... go figure

        # 2. Tweak FC layer with the num_classes provided
        # Custom handling of models that have non-standard classifier layers
        if 'squeezenet' in model_name:
            final_conv = nn.Conv2d(512, num_classes, kernel_size=1)
            classifier = nn.Sequential(
                nn.Dropout(p=0.5),
                final_conv,
                nn.ReLU(inplace=True),
                nn.AvgPool2d(13, stride=1)
            )
            model.classifier = classifier
            model.num_classes = num_classes
        elif 'vgg' in model_name:
            classifier = nn.Sequential(
                nn.Linear(512 * 7 * 7, 4096),
                nn.ReLU(True),
                nn.Dropout(),
                nn.Linear(4096, 4096),
                nn.ReLU(True),
                nn.Dropout(),
                nn.Linear(4096, num_classes)
            )
            model.classifier = classifier
        elif 'inception3' in model_name.lower() or 'inception_v3' in model_name.lower():
            # Two FC layers if aux_logits are enabled
            if getattr(model, 'aux_logits', False):
                model.AuxLogits = InceptionAux(768, num_classes)
            model.fc = nn.Linear(2048, num_classes)

        elif 'dpn' in model_name.lower():
            old_fc = getattr(model, fc_name)
            new_fc = nn.Conv2d(old_fc.in_channels, num_classes, kernel_size=1, bias=True)
            setattr(model, fc_name, new_fc)
        else:  # perform standard replacement of the last FC / Linear layer with a new one
            old_fc = getattr(model, fc_name)
            new_fc = nn.Linear(old_fc.in_features, num_classes)
            setattr(model, fc_name, new_fc)

        return model

    elif type == 'segmentation':
        if model_name == 'Enet':                                            # standard enet
            net = ENet(num_classes=num_classes)
            if pretrained:
                print("WARN: Enet does not have a pretrained model! Empty model as been created instead.")
        elif model_name == 'deeplabv2_ASPP':                                # Deeplab Atrous Convolutions
            net = DeepLabv2_ASPP(num_classes=num_classes, pretrained=pretrained)
        elif model_name == 'deeplabv2_FOV':                                 # Deeplab FOV
            net = DeepLabv2_FOV(num_classes=num_classes, pretrained=pretrained)
        elif model_name == 'deeplabv3':                                     # Deeplab V3!
            net = DeepLabv3(num_classes=num_classes, pretrained=pretrained)
        elif model_name == 'deeplabv3_Plus':  # Deeplab V3!
            net = DeepLabv3_plus(num_classes=num_classes, pretrained=pretrained)
        elif 'DRN_' in model_name:
            net = DRNSeg(model_name=model_name, classes=num_classes, pretrained=pretrained)
        elif model_name == 'FRRN_A':                                        # FRRN
            net = frrn(num_classes=num_classes, model_type='A')
            if pretrained:
                print("FRRN_A Does not have a pretrained model! Empty model has been created instead.")
        elif model_name == 'FRRN_B':                                        # FRRN
            net = frrn(num_classes=num_classes, model_type='B')
            if pretrained:
                print("FRRN_B Does not have a pretrained model! Empty model has been created instead.")
        elif model_name == 'FusionNet':                                     # FusionNet
            net = FusionNet(num_classes=num_classes)
            if pretrained:
                print("FusionNet Does not have a pretrained model! Empty model has been created instead.")
        elif model_name == 'GCN':                                           # GCN Resnet
            net = GCN(num_classes=num_classes, pretrained=pretrained)
        elif model_name == 'GCN_VisDa':                                     # Another GCN Implementation
            net = GCN_VisDa(num_classes=num_classes, input_size=input_size, pretrained=pretrained)
        elif model_name == 'GCN_Densenet':                                     # Another GCN Implementation
            net = GCN_DENSENET(num_classes=num_classes, input_size=input_size, pretrained=pretrained)
        elif model_name == 'GCN_PSP':                                     # Another GCN Implementation
            net = GCN_PSP(num_classes=num_classes, input_size=input_size, pretrained=pretrained)
        elif model_name == 'GCN_NASNetA':                                     # Another GCN Implementation
            net = GCN_NASNET(num_classes=num_classes, input_size=input_size, pretrained=pretrained)
        elif model_name == 'GCN_Resnext':                                     # Another GCN Implementation
            net = GCN_RESNEXT(num_classes=num_classes, input_size=input_size, pretrained=pretrained)
        elif model_name == 'Linknet':                                       # Linknet34
            net = LinkNet34(num_classes=num_classes, pretrained=pretrained)
        elif model_name == 'PSPNet':
            net = PSPNet(num_classes=num_classes, pretrained=pretrained, backend='resnet101')
        elif model_name == 'Resnet_DUC':
            net = ResNetDUC(num_classes=num_classes, pretrained=pretrained)
        elif model_name == 'Resnet_DUC_HDC':
            net = ResNetDUCHDC(num_classes=num_classes, pretrained=pretrained)
        elif model_name == 'Resnet_GCN':                                    # GCN Resnet 2
            net = ResnetGCN(num_classes=num_classes, pretrained=pretrained)
        elif model_name == 'Segnet':                                          # standard segnet
            net = SegNet(num_classes=num_classes, pretrained=pretrained)
        elif model_name == 'TEST_DiLinknet':
            net = TEST_DiLinknet(num_classes=num_classes, pretrained=False)
        elif model_name == 'TEST_DLR_Resnet':
            net = create_DLR_V3_pretrained(num_classes=num_classes)
        elif model_name == 'TEST_DLX_Resnet':
            net = create_DLX_V3_pretrained(num_classes=num_classes)
        elif model_name == 'TEST_PSPNet2':
            net = TEST_PSPNet2(num_classes=num_classes)
        elif model_name == 'TEST_DLV2':
            net = TEST_DLV2(n_classes=num_classes, n_blocks=[3, 4, 23, 3], pyramids=[6, 12, 18, 24])
            net = TEST_DLV3_Xception(n_classes=num_classes, os=8, pretrained=True, _print=False)
        elif model_name == 'TEST_DLV3':
            net = TEST_DLV3(n_classes=num_classes, n_blocks=[3, 4, 23, 3], pyramids=[12, 24, 36], grids=[1, 2, 4], output_stride=8)
        elif model_name == 'TEST_LinkCeption':
            net = TEST_LinkCeption(num_classes=num_classes)
        elif model_name == 'TEST_LinkDensenet121':
            net = TEST_LinkDenseNet121(num_classes=num_classes)
        elif model_name == 'TEST_Linknet50':
            net = TEST_Linknet101(num_classes=num_classes)
        elif model_name == 'TEST_Linknet101':
            net = TEST_Linknet101(num_classes=num_classes)
        elif model_name == 'TEST_Linknet152':
            net = TEST_Linknet152(num_classes=num_classes)
        elif model_name == 'TEST_Linknext':
            net = TEST_Linknext(num_classes=num_classes)
        elif model_name == 'TEST_FCDensenet':
            net = TEST_FCDensenet(out_channels=num_classes)
        elif model_name == 'TEST_Tiramisu57':
            net = TEST_Tiramisu57(num_classes=num_classes)
        elif model_name == 'TEST_Unet_nested_dilated':
            net = TEST_Unet_nested_dilated(n_classes=num_classes)
        elif model_name == 'TEST_Unet_plus_plus':
            net = Unet_Plus_Plus(in_channels=3, n_classes=num_classes)
        elif model_name == 'Tiramisu57':  # Tiramisu
            net = FCDenseNet57(n_classes=num_classes)
            if pretrained:
                print("Tiramisu67 Does not have a pretrained model! Empty model has been created instead.")
        elif model_name == 'Tiramisu67':                                     # Tiramisu
            net = FCDenseNet67(n_classes=num_classes)
            if pretrained:
                print("Tiramisu67 Does not have a pretrained model! Empty model has been created instead.")
        elif model_name == 'Tiramisu103':                                   # Tiramisu
            net = FCDenseNet103(n_classes=num_classes)
            if pretrained:
                print("Tiramisu103 Does not have a pretrained model! Empty model has been created instead.")
        elif model_name == 'Unet':                                          # standard unet
            net = UNet(num_classes=num_classes)
            if pretrained:
                print("UNet Does not have a pretrained model! Empty model has been created instead.")
        elif model_name == 'UNet256':                                       # Unet for 256px square imgs
            net = UNet256(in_shape=(3,256,256))
            if pretrained:
                print("UNet256 Does not have a pretrained model! Empty model has been created instead.")
        elif model_name == 'UNet512':                                       # Unet for 512px square imgs
            net = UNet512(in_shape=(3, 512, 512))
            if pretrained:
                print("UNet512 Does not have a pretrained model! Empty model has been created instead.")
        elif model_name == 'UNet1024':                                      # Unet for 1024px square imgs
            net = UNet1024(in_shape=(3, 1024, 1024))
            if pretrained:
                print("UNet1024 Does not have a pretrained model! Empty model has been created instead.")
        elif model_name == 'UNet960':                                       # Another Unet specifically with 960px resolution
            net = UNet960(filters=12)
            if pretrained:
                print("UNet960 Does not have a pretrained model! Empty model has been created instead.")
        elif model_name == 'unet_dilated':                                  # dilated unet
            net = uNetDilated(num_classes=num_classes)
        elif model_name == 'Unet_res':                                      # residual unet
            net = UNetRes(num_class=num_classes)
            if pretrained:
                print("UNet_res Does not have a pretrained model! Empty model has been created instead.")
        elif model_name == 'UNet_stack':                                    # Stacked Unet variation with resnet connections
            net = UNet_stack(input_size=(input_size, input_size), filters=12)
            if pretrained:
                print("UNet_stack Does not have a pretrained model! Empty model has been created instead.")
        else:
            raise Exception('Combination of type: {} and model_name: {} is not valid'.format(type, model_name))

    return net

def get_supported_models(type):
    '''

    :param type: str
        one of {'classification', 'segmentation'}
    :return: list (strings) of supported models
    '''

    if type == 'segmentation':
        return ['Enet',
                'deeplabv2_ASPP',
                'deeplabv2_FOV',
                'deeplabv3',
                'deeplabv3_Plus',
                'DRN_C_42',
                'DRN_C_58',
                'DRN_D_38',
                'DRN_D_54',
                'DRN_D_105',
                'FRRN_A',
                'FRRN_B',
                'FusionNet',
                'GCN',
                'GCN_VisDa',
                'GCN_Densenet',
                'GCN_PSP',
                'GCN_NASNetA',
                'GCN_Resnext',
                'Linknet',
                'PSPNet',
                'Resnet_DUC',
                'Resnet_DUC_HDC',
                'Resnet_GCN',
                'Segnet',
                'Tiramisu67',
                'Tiramisu103',
                'Unet',
                'UNet256',
                'UNet512',
                'UNet1024',
                'UNet960',
                'unet_dilated',
                'Unet_res',
                'UNet_stack']
    elif type == 'classification':
        # excludes are just filenames that are in the 'classification' directory (and are not names of real networks in __init__.py)
        excludes = ['dpn', 'inception_resv2_wide', 'nasnet', 'nasnet_mobile', 'pnasnet', 'pyramid_resnet',
                    'resnet_swish', 'resnext_features', 'resnext', 'se_module', 'se_resnet', 'senet', 'wide_resnet', 'wide_resnet_2',
                    'resnet', 'vgg', 'squeezenet', 'inception', 'densenet']         # <-- this line reserved for exclusions from torchvision
        wick_names = [x for x in classification.__dict__.keys() if '__' not in x]     # includes directory and filenames
        pt_names = [x for x in torch_models.__dict__.keys() if '__' not in x]  # includes directory and filenames
        names = wick_names + pt_names
        return [x for x in names if x not in excludes]      # filtered list
    else:
        raise Exception('Incorrect type specified. Expected one of: {classification, segmentation}')

def _get_untrained_model(model_name, num_classes):
    '''
    Primarily, this method exists to return an untrained / vanilla version of a specified (pretrained) model.
    This is on best-attempt basis only and may be out of sync with actual model definitions. The code is manually maintained.

    :param model_name: Lower-case model names are pretrained by convention.
    :param num_classes: Number of classes to initialize the vanilla model with.

    :return: default model for the model_name with custom number of classes
    '''

    if model_name.startswith('bninception'):
        return classification.BNInception(num_classes=num_classes)
    elif model_name.startswith('densenet'):
        return torch_models.DenseNet(num_classes=num_classes)
    elif model_name.startswith('dpn'):
        return classification.DPN(num_classes=num_classes)
    elif model_name.startswith('inceptionresnetv2'):
        return classification.InceptionResNetV2(num_classes=num_classes)
    elif model_name.startswith('inception_v3'):
        return torch_models.Inception3(num_classes=num_classes)
    elif model_name.startswith('inceptionv4'):
        return classification.InceptionV4(num_classes=num_classes)
    elif model_name.startswith('nasnetalarge'):
        return classification.NASNetALarge(num_classes=num_classes)
    elif model_name.startswith('nasnetamobile'):
        return classification.NASNetAMobile(num_classes=num_classes)
    elif model_name.startswith('pnasnet5large'):
        return classification.PNASNet5Large(num_classes=num_classes)
    elif model_name.startswith('polynet'):
        return classification.PolyNet(num_classes=num_classes)
    elif model_name.startswith('pyresnet'):
        return classification.PyResNet(num_classes=num_classes)
    elif model_name.startswith('resnet'):
        return torch_models.ResNet(num_classes=num_classes)
    elif model_name.startswith('resnext101_32x4d'):
        return classification.ResNeXt101_32x4d(num_classes=num_classes)
    elif model_name.startswith('resnext101_64x4d'):
        return classification.ResNeXt101_64x4d(num_classes=num_classes)
    elif model_name.startswith('se_inception'):
        return classification.SEInception3(num_classes=num_classes)
    elif model_name.startswith('se_resnext50_32x4d'):
        return classification.se_resnext50_32x4d(num_classes=num_classes, pretrained=None)
    elif model_name.startswith('se_resnext101_32x4d'):
        return classification.se_resnext101_32x4d(num_classes=num_classes, pretrained=None)
    elif model_name.startswith('senet154'):
        return classification.senet154(num_classes=num_classes, pretrained=None)
    elif model_name.startswith('se_resnet50'):
        return classification.se_resnet50(num_classes=num_classes, pretrained=None)
    elif model_name.startswith('se_resnet101'):
        return classification.se_resnet101(num_classes=num_classes, pretrained=None)
    elif model_name.startswith('se_resnet152'):
        return classification.se_resnet152(num_classes=num_classes, pretrained=None)
    elif model_name.startswith('squeezenet1_0'):
        return torch_models.squeezenet1_0(num_classes=num_classes, pretrained=False)
    elif model_name.startswith('squeezenet1_1'):
        return torch_models.squeezenet1_1(num_classes=num_classes, pretrained=False)
    elif model_name.startswith('xception'):
        return classification.Xception(num_classes=num_classes)
    else:
        raise ValueError('No vanilla model found for model name: {}'.format(model_name))

# We solve the dimensionality mismatch between final layers in the constructed vs pretrained modules at the data level.
def diff_states(dict_canonical, dict_subset):
    names1, names2 = (list(dict_canonical.keys()), list(dict_subset.keys()))

    # Sanity check that param names overlap
    # Note that params are not necessarily in the same order
    # for every pretrained model
    not_in_1 = [n for n in names1 if n not in names2]
    not_in_2 = [n for n in names2 if n not in names1]
    assert len(not_in_1) == 0
    assert len(not_in_2) == 0

    for name, v1 in dict_canonical.items():
        v2 = dict_subset[name]
        assert hasattr(v2, 'size')
        if v1.size() != v2.size():
            yield (name, v1)
            
def load_checkpoint(model, checkpoint_path, use_gpu):
    '''
    Loads weights from a checkpoint into memory. If model is not None then the weights are loaded into the model.
    :param model: the model object (Note: this can be set to None if you just want the checkpoint data)
    :param checkpoint_path: str
        path to a pretrained network to load weights from
    :param use_gpu: bool
        whether this model will be loaded onto gpu or cpu
    :return: checkpoint
    '''

    # Handle incompatibility between pytorch0.4 and pytorch0.4.x
    # Source: https://discuss.pytorch.org/t/question-about-rebuild-tensor-v2/14560/2
    import torch._utils
    try:
        torch._utils._rebuild_tensor_v2
    except AttributeError:
        def _rebuild_tensor_v2(storage, storage_offset, size, stride, requires_grad, backward_hooks):
            tensor = torch._utils._rebuild_tensor(storage, storage_offset, size, stride)
            tensor.requires_grad = requires_grad
            tensor._backward_hooks = backward_hooks
            return tensor

        torch._utils._rebuild_tensor_v2 = _rebuild_tensor_v2

    checkpoint = None
    if checkpoint_path:
        # load data directly from a checkpoint
        checkpoint_path = os.path.expanduser(checkpoint_path)
        if os.path.isfile(checkpoint_path):
            if use_gpu:
                print("=> resuming model on GPU from checkpoint '{}'".format(checkpoint_path))
                checkpoint = torch.load(checkpoint_path)
            else:
                print("=> resuming model on CPU from checkpoint '{}'".format(checkpoint_path))
                checkpoint = torch.load(checkpoint_path, map_location=lambda storage, loc: storage)

            pretrained_state = checkpoint['state_dict']
            print("INFO: => loaded checkpoint '{}' (epoch {})".format(checkpoint_path, checkpoint.get('epoch')))
            print('INFO: => checkpoint model name: ', checkpoint.get('modelname'), ' Make sure the checkpoint model name matches your model!!!')
        else:
            print("INFO: => no checkpoint found at '{}'.   Exiting!!".format(checkpoint_path))
            exit()

        if checkpoint.get('proc_type') == 'multi_gpu' or checkpoint.get('proc_type') == 'multi-gpu':
            # handle the case where the training was done on multiple GPUs but the testing is being performed on a CPU or single GPU
            print("INFO: Converting pretrained model from multi-GPU configuration to a single GPU/CPU configuration before resuming")
            # create new OrderedDict that does not contain `module.`
            from collections import OrderedDict
            new_state_dict = OrderedDict()
            for k, v in pretrained_state.items():
                if k.startswith('module.'):
                    name = k[7:]  # remove `module.`
                    new_state_dict[name] = v
                else:
                    new_state_dict[k] = v
            checkpoint['state_dict'] = new_state_dict

        # finally load the model weights
        if model:
            print('INFO: => Attempting to load checkpoint data onto model.')
            model.load_state_dict(checkpoint['state_dict'])
    return checkpoint