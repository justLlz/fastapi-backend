CREATE TABLE `device`
(
    `id`             bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
    `number`         varchar(128)    NOT NULL COMMENT '设备编号',
    `name`           varchar(32)     NOT NULL COMMENT '设备名称',
    `gpu_brand`      varchar(32)     NOT NULL COMMENT '品牌型号',
    `gpu_model`      varchar(32)     NOT NULL COMMENT '显卡型号',
    `gpu_number`     varchar(32)     NOT NULL COMMENT '显卡编号',
    `memory`         varchar(32)     NOT NULL COMMENT '内存',
    `hard_disk`      varchar(32)     NOT NULL COMMENT '硬盘',
    `operate_system` varchar(32)     NOT NULL COMMENT '操作系统',
    `mac_address`    varchar(32)     NOT NULL COMMENT 'mac地址',
    `ip_address`     varchar(32)     NOT NULL COMMENT 'ip地址',
    `supplier`       varchar(32)     NOT NULL COMMENT '供应商',
    `location`       varchar(16)     NOT NULL COMMENT '放置位置',
    `cui_version`    varchar(32)     NOT NULL COMMENT 'cui 版本',
    `other_info`     varchar(128)    NOT NULL COMMENT '其他信息',
    `status`         varchar(8)      NOT NULL COMMENT '状态: 关机-off,使用中-on,闲置中-free',
    `asset_status`   varchar(8)      NOT NULL COMMENT '资产状态: 已经上线-online, 未上线-offline',
    `remarks`        varchar(128)    NOT NULL COMMENT '备注',
    `stocked_at`     bigint unsigned NOT NULL COMMENT '入库时间',
    `updated_at`     bigint unsigned NOT NULL COMMENT '更新时间',
    `created_at`     bigint unsigned NOT NULL COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `number_name` (`number`, `name`)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci COMMENT ='设备信息表';