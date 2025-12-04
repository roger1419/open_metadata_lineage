----------------------------------------------------------------
-- 程序功能： 海外短剧-用户充值曝光信息表
-- 程序名： P_ads_bi_sv_user_recharge_expo_info_di
-- 目标表： ads.ads_bi_sv_user_recharge_expo_info_di
-- 负责人： roger
-- 开发日期：2025/11/19
-- 版本号： v1.0
----------------------------------------------------------------

insert into ads.ads_bi_sv_user_recharge_expo_info_di
-- 取用户登录第一条充值曝光信息
with recharge_exposure_tmp as (
     select dt
           ,login_id
           ,zffs_list
           ,event_strategy_id
           ,app_id
           ,app_core_ver
           ,czlx
           ,os
           ,product_id
           ,row_number() over(partition by login_id order by event_tm) as rn
     from ods_log.ods_sensors_cd_video_production_rechargeexposure
     where product_id = 6833 
       and dt = '${bf_1_dt}'
       and cast(login_id as bigint) is not null
     )

select a1.dt                       as dt                     -- 日期
      ,a1.usr_id                   as user_id                -- 用户id
      ,zffs_array[generate_series] as zffs                   -- 支付渠道
      ,generate_series             as zffs_rank              -- 曝光位次
      ,a1.event_strategy_id        as strategy_id            -- 策略id
      ,a1.app_id                   as app_id                 -- 应用id
      ,a1.app_core_ver             as app_core_ver           -- core
      ,a1.czlx                     as shop_item              -- 充值类型名称
      ,a1.os                       as mt                     -- 移动终端
      ,a1.user_type                as user_type              -- 用户类型名称
      ,a1.reg_country              as reg_country            -- 注册国家编码
      ,a1.CurrentLanguage2         as current_language2      -- 投放语言
      ,a1.lang_name                as current_language2_name -- 投放语言名称
      ,now()                       as etl_tm                 -- etl时间
from (select b1.dt
            ,b1.login_id                            as usr_id
            ,split(b1.zffs_list, ",")               as zffs_array
            ,array_length(split(b1.zffs_list, ",")) as size
            ,b1.event_strategy_id
            ,b1.app_id
            ,b1.app_core_ver
            ,b1.czlx
            ,b1.os
            ,b2.CurrentLanguage2
            ,b3.user_type
            ,b3.reg_country
            ,b4.cd_val_desc                         as lang_name
      from recharge_exposure_tmp                                   as b1
      left join ods.ods_tidb_short_video_accountinfo               as b2
        on b1.login_id = b2.id
      left join dws.dws_user_short_video_wide_active_period_ed     as b3
        on b3.dt = "${bf_1_dt}"
       and b3.period_type = "ctt"
       and b3.product_id = 6833
       and b1.login_id = b3.user_id
      left join dim.dim_pub_code_mapping_dict b4
        on b4.app_plat = "pub"
       and b4.cd_col = "lang_cd"
       and b2.CurrentLanguage2 = b4.cd_val
      where b1.rn = 1
      ) a1,
generate_series(1, size)
;