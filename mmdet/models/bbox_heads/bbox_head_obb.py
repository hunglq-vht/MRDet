import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.modules.utils import _pair

from mmdet.core import (auto_fp16, force_fp32, delta2rec,
                        bbox_target_rbbox, rbbox_target_rbbox,
                        multiclass_poly_nms_8_points, rbboxRec2Poly)
from ..builder import build_loss
from ..losses import accuracy
from ..registry import HEADS


@HEADS.register_module
class BBoxHeadOBB(nn.Module):
    """Simplest RoI head, with only two fc layers for classification and
    regression respectively"""

    def __init__(self,
                 with_avg_pool=False,
                 with_cls=True,
                 with_reg=True,
                 roi_feat_size=7,
                 in_channels=256,
                 num_classes=81,
                 target_means=[0., 0., 0., 0., 0.],
                 target_stds=[0.1, 0.1, 0.2, 0.2, 0.1],
                 reg_class_agnostic=False,
                 loss_cls=dict(
                     type='CrossEntropyLoss',
                     use_sigmoid=False,
                     loss_weight=1.0),
                 loss_bbox=dict(
                     type='SmoothL1Loss', beta=1.0, loss_weight=1.0)):
        super(BBoxHeadOBB, self).__init__()
        assert with_cls or with_reg
        self.with_avg_pool = with_avg_pool
        self.with_cls = with_cls
        self.with_reg = with_reg


        self.roi_feat_size = _pair(roi_feat_size)
        self.roi_feat_area = self.roi_feat_size[0] * self.roi_feat_size[1]
        self.in_channels = in_channels
        self.num_classes = num_classes
        self.target_means = target_means
        self.target_stds = target_stds
        self.reg_class_agnostic = reg_class_agnostic
        self.fp16_enabled = False

        self.loss_cls = build_loss(loss_cls)
        self.loss_bbox = build_loss(loss_bbox)

        in_channels = self.in_channels # light-head-rcnn:10
        if self.with_avg_pool:
            self.avg_pool = nn.AvgPool2d(self.roi_feat_size)
        else:
            in_channels *= self.roi_feat_area # light-head-rcnn:10*7*7
        if self.with_cls:
            self.fc_cls = nn.Linear(in_channels, num_classes)
            # 会将特征图展开，这里的in_channels = self.inchannels * roi_feat_area
        if self.with_reg:
            out_dim_reg = 5 if reg_class_agnostic else 5 * num_classes
            self.fc_reg = nn.Linear(in_channels, out_dim_reg)
        self.debug_imgs = None

    def init_weights(self):
        if self.with_cls:
            nn.init.normal_(self.fc_cls.weight, 0, 0.01)
            nn.init.constant_(self.fc_cls.bias, 0)
        if self.with_reg:
            nn.init.normal_(self.fc_reg.weight, 0, 0.001)
            nn.init.constant_(self.fc_reg.bias, 0)

    @auto_fp16()
    def forward(self, x):
        if self.with_avg_pool:
            x = self.avg_pool(x)
        x = x.view(x.size(0), -1)
        cls_score = self.fc_cls(x) if self.with_cls else None
        bbox_pred = self.fc_reg(x) if self.with_reg else None
        return cls_score, bbox_pred

    def get_target_hbbox2rbbox(self, sampling_results, gt_rbboxes_poly, cfg):
        pos_proposals = [res.pos_bboxes for res in sampling_results]
        neg_proposals = [res.neg_bboxes for res in sampling_results]
        # pos_gt_bboxes = [res.pos_gt_bboxes for res in sampling_results]
        pos_assigned_gt_inds = [res.pos_assigned_gt_inds for res in sampling_results]

        pos_gt_labels = [res.pos_gt_labels for res in sampling_results]
        reg_classes = 1 if self.reg_class_agnostic else self.num_classes
        cls_reg_targets = bbox_target_rbbox(
            pos_proposals,
            neg_proposals,
            pos_gt_labels,
            pos_assigned_gt_inds,
            gt_rbboxes_poly,
            cfg,
            reg_classes,
            target_means=self.target_means,
            target_stds=self.target_stds)

        # print(bbox_targets)
        return cls_reg_targets


    @force_fp32(apply_to=('cls_score', 'bbox_pred'))
    def loss_hbbox2rbbox(self,
             cls_score,
             bbox_pred,
             labels,
             label_weights,
             bbox_targets,
             bbox_weights,
             reduction_override=None):
        losses = dict()
        if cls_score is not None:
            avg_factor = max(torch.sum(label_weights > 0).float().item(), 1.)
            losses['loss_cls'] = self.loss_cls(
                cls_score,
                labels,
                label_weights,
                avg_factor=avg_factor,
                reduction_override=reduction_override)
            losses['acc'] = accuracy(cls_score, labels)
        if bbox_pred is not None:
            pos_inds = labels > 0
            if self.reg_class_agnostic:
                pos_bbox_pred = bbox_pred.view(bbox_pred.size(0), 5)[pos_inds]
            else:
                pos_bbox_pred = bbox_pred.view(bbox_pred.size(0), -1,
                                               5)[pos_inds, labels[pos_inds]]
            losses['loss_bbox'] = self.loss_bbox(
                pos_bbox_pred,
                bbox_targets[pos_inds],
                bbox_weights[pos_inds],
                avg_factor=bbox_targets.size(0),
                reduction_override=reduction_override)
        return losses


    def get_target_rbbox2rbbox(self, sampling_results, gt_rbboxes_rec, rcnn_train_cfg):
        pos_proposals = [res.pos_bboxes for res in sampling_results]
        neg_proposals = [res.neg_bboxes for res in sampling_results]
        pos_assigned_gt_inds = [res.pos_assigned_gt_inds for res in sampling_results]
        pos_gt_labels = [res.pos_gt_labels for res in sampling_results]
        reg_classes = 1 if self.reg_class_agnostic else self.num_classes
        cls_reg_targets = rbbox_target_rbbox(
            pos_proposals,
            neg_proposals,
            pos_assigned_gt_inds,
            gt_rbboxes_rec,
            pos_gt_labels,
            rcnn_train_cfg,
            reg_classes,
            target_means=self.target_means,
            target_stds=self.target_stds)
        return cls_reg_targets

    def loss(self,
             cls_score,
             bbox_pred,
             labels,
             label_weights,
             bbox_targets,
             bbox_weights,
             reduction_override=None):
        losses = dict()
        if cls_score is not None:
            avg_factor = max(torch.sum(label_weights > 0).float().item(), 1.)
            losses['loss_cls'] = self.loss_cls(
                cls_score,
                labels,
                label_weights,
                avg_factor=avg_factor,
                reduction_override=reduction_override)
            losses['acc'] = accuracy(cls_score, labels)

        if bbox_pred is not None:
            pos_inds = labels > 0
            if self.reg_class_agnostic:
                pos_bbox_pred = bbox_pred.view(bbox_pred.size(0), 5)[pos_inds]
            else:
                pos_bbox_pred = bbox_pred.view(bbox_pred.size(0), -1,
                                               5)[pos_inds, labels[pos_inds]]
            losses['loss_bbox'] = self.loss_bbox(
                pos_bbox_pred,
                bbox_targets[pos_inds],
                bbox_weights[pos_inds],
                avg_factor=bbox_targets.size(0),
                reduction_override=reduction_override)

        return losses


    @force_fp32(apply_to=('cls_score', 'bbox_pred'))
    def get_det_rbbox2rbbox(self,
                       rrois,
                       cls_score,
                       bbox_pred,
                       img_shape,
                       scale_factor,
                       rescale=False,
                       cfg=None):
        if isinstance(cls_score, list):
            cls_score = sum(cls_score) / float(len(cls_score))
        scores = F.softmax(cls_score, dim=1) if cls_score is not None else None

        if bbox_pred is not None:
            rbboxes_rec = delta2rec(bbox_pred, rrois[:, 1:], self.target_means,
                                           self.target_stds, img_shape)
        else:
            rbboxes_rec = rrois[:, 1:]

        if rescale:
            rbboxes_rec[:, 0::5] /= scale_factor
            rbboxes_rec[:, 1::5] /= scale_factor
            rbboxes_rec[:, 2::5] /= scale_factor
            rbboxes_rec[:, 3::5] /= scale_factor
        rbboxes_poly = rbboxRec2Poly(rbboxes_rec, img_shape)
        if cfg is None:
            return rbboxes_rec, scores
        else:
            det_rbboxes, det_labels = multiclass_poly_nms_8_points(rbboxes_poly, scores,
                                                                   cfg.score_thr,
                                                                   cfg.nms,
                                                                   max_num=cfg.max_per_img)

            return det_rbboxes, det_labels


