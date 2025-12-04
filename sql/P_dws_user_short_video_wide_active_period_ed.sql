insert into dws.dws_user_short_video_wide_active_period_ed
-- -----------------------ctt活跃用户的主表 ------------------------
with active as (
    select
        a.dt, a.product_id, a.user_id, a.corever, a.mt, a.current_language, a.current_language2,
        a.reg_country, a.country_level, a.reg_time, a.reg_days, a.sex, a.is_acc_login, a.is_has_email, a.popularize_series_code,
        case when a.reg_days=0 then 'D0'
             when a.reg_days>=1 and a.reg_days<=7 then 'D1-D7'
             when a.reg_days>=8 and a.reg_days<=30 then 'D8-D30'
             when a.reg_days>=31 and b.user_id is not null then 'D31+_stock_user'
             when a.reg_days>=31 and b.user_id is null then 'D31+_backflow_user'
             else 'D31+_backflow_user' end as user_type,
        if(b.user_id is not null,1,0) as is_l7_active
    from (
             select
                 dt, product_id, user_id, corever, mt, current_language, current_language2,
                 reg_country, country_level, reg_time, reg_days, sex, is_acc_login, is_has_email, popularize_series_code
             from dws.dws_user_short_video_wide_active_ed
             where dt = '${bf_1_dt}'
         ) a
             left join (
        select product_id, user_id
        from dws.dws_user_short_video_wide_active_ed
        where dt >= date_sub('${bf_1_dt}',interval 7 day) and dt < '${bf_1_dt}'
        group by product_id, user_id
    ) b on a.product_id=b.product_id and a.user_id=b.user_id
),

rmt as (
 select
     product_id, user_id, max(dt) as install_dt
 from dws.dws_srsv_wide_user_type_info_di
 where dt>=date_sub('${bf_1_dt}',interval 6 month ) and dt <='${bf_1_dt}' and  user_period=3 and product_id in(6833)
 group by 1,2
 union all
 select
     product_id, user_id, max(stat_period) as install_dt
 from dws.dws_wide_video_cn_user_type_info_ed
 where user_period=3 and period_types=1 and stat_period>=date_sub('${bf_1_dt}',interval 6 month ) and stat_period <='${bf_1_dt}' and product_id in(6883)
 group by 1,2
),
-- -----------rmt用户主表，来源于 active 子查询 -------------------------------
rmt_user_type as(
 select a.dt, a.product_id, a.user_id, a.corever, a.mt, a.current_language, a.current_language2,
        a.reg_country, a.country_level, a.reg_time, a.reg_days, a.sex, a.is_acc_login, a.is_has_email, a.popularize_series_code,
        case when datediff(a.dt,b.install_dt)=0 then 'D0'
             when datediff(a.dt,b.install_dt)>=1 and datediff(a.dt,b.install_dt)<=7 then 'D1-D7'
             when datediff(a.dt,b.install_dt)>=8 and datediff(a.dt,b.install_dt)<=30 then 'D8-D30'
             when datediff(a.dt,b.install_dt)>=31 and is_l7_active=1 then 'D31+_stock_user'
             else 'D31+_backflow_user'
            end as user_type,
        if(b.user_id is not null,1,0) as is_rmt
 from active a left join rmt b on a.product_id=b.product_id and a.user_id=b.user_id
)


select a.dt,
       'ctt' as period_type,
       a.product_id,
       a.user_id,
       a.user_type,
       a.corever,
       a.mt,
       a.current_language,
       a.current_language2,
       b.source_chl AS source_chl,
       a.reg_country,
       a.country_level,
       a.reg_time,
       a.reg_days,
       a.sex,
       a.is_acc_login,
       a.is_has_email,
       a.popularize_series_code,
       now() as etl_time
from active a
LEFT JOIN dim.dim_short_video_user_accountinfo b
ON a.product_id = b.product_id
AND a.user_id = b.user_id
union all
select a.dt,
       'rmt' as period_type,
       a.product_id,
       a.user_id,
       a.user_type,
       a.corever,
       a.mt,
       a.current_language,
       a.current_language2,
       b.source_chl AS source_chl,
       a.reg_country,
       a.country_level,
       a.reg_time,
       a.reg_days,
       a.sex,
       a.is_acc_login,
       a.is_has_email,
       a.popularize_series_code,
       now() as etl_time
from rmt_user_type a
LEFT JOIN dim.dim_short_video_user_accountinfo b
       ON a.product_id = b.product_id
           AND a.user_id = b.user_id
;