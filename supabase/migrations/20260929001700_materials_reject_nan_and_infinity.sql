-- float8 では NaN がどの値よりも大きい扱いなので、create_materials の 0 < all (...) では
-- NaN も Infinity も通ってしまう。有限の値だけを保存できるようにする。
-- NaN <> NaN は偽（Postgres は NaN 同士を等しいとみなす）なので、<> all で NaN の混入を弾ける。
alter table public.materials
  add constraint materials_values_finite check (
        'NaN'::float8 <> all (wavelengths_nm) and 'Infinity'::float8 > all (wavelengths_nm)
    and 'NaN'::float8 <> all (n)              and 'Infinity'::float8 > all (n)
    and 'NaN'::float8 <> all (k)              and 'Infinity'::float8 > all (k)
  );
