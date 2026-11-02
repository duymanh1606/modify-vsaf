# Fallback: trích nghiệp vụ từ source code (khi HLD/WBS/PRD thiếu)

Dùng khi tài liệu thiết kế thiếu ERD / actor / flow. **Code là sự thật** — trích rồi **ghi kèm nguồn**
(`file:line`), phần suy diễn không chắc → `[Cần xác nhận]`. Bảng dưới cho stack Java/Spring (các repo reconciliation);
điều chỉnh dấu hiệu cho stack khác.

| Cần suy ra | Tìm ở đâu trong code |
|---|---|
| **Thực thể ERD** (bảng, trường, khóa) | `@Entity` / `@Table` / `@Id` / `@Column` (JPA); `CREATE TABLE`, migration (Flyway/Liquibase); `@ManyToOne` / `@OneToMany` / `@JoinColumn` = quan hệ 1:N / khóa ngoại |
| **Actor + quyền** | `@RestController` + endpoint; `@PreAuthorize` / `@Secured` / role guard; header user (vd `X-User`); nhóm endpoint theo controller = nhóm chức năng theo vai trò |
| **Quy trình nghiệp vụ** | Luồng gọi trong `@Service` (orchestration); `@Scheduled` / cron / job (bước chạy ngầm); `@KafkaListener` / consumer / producer (dòng chảy async); trạng thái rẽ nhánh theo `if`/enum |
| **Hệ thống ngoài** | `@FeignClient` / `RestTemplate` / `WebClient` base-url; cấu hình SFTP/FTP host đối tác; client OAuth/Keycloak; tên topic Kafka out |
| **Kho dữ liệu trung gian** | MinIO/S3 client; thư mục file tạm; bảng staging; cache Redis |
| **Trạng thái (vòng đời)** | enum `*Status` / `*State` + chỗ gán/chuyển; hằng số `Constant.*`; điều kiện `if` trên status trong service |
| **Phân rã chức năng (§6)** | FE: component/screen/route; BE-kết nối: controller/endpoint/adapter; BE-hạ tầng: job/consumer/producer/scheduler — **soát cả 3 loại, đừng bỏ phần chạy ngầm** |

**Cách làm nhanh:** grep theo dấu hiệu ở trên trong các repo code (reconciliation-service / -process /
-external-data-service / -internal-service / -admin-service / -fe), đối chiếu với HLD/WBS để lấp chỗ trống, KHÔNG
thay thế tài liệu thiết kế khi nó đã có. Ưu tiên: HLD → WBS → PRD → code (code chỉ để lấp).
