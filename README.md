# VIETCASA – Phần mềm quản lý nhân sự

Bản triển khai nội bộ chạy trên Cloudflare Worker và D1.

## Cài đặt

1. Cài Node.js bản LTS và đăng nhập vào tài khoản Cloudflare của VIETCASA.
2. Chạy `cai-dat.cmd` để cài công cụ, tạo cơ sở dữ liệu và triển khai Worker.
3. Đặt mã cài đặt bằng lệnh `npx wrangler secret put MA_CAI_DAT` nếu trình cài đặt chưa yêu cầu.

Để cập nhật, chạy `cap-nhat.cmd`. Cấu hình cơ sở dữ liệu D1 hiện có được giữ nguyên.

Bản quyền thuộc Vietcasa - Lưu hành nội bộ | Made by phuocnhtvietcasa
