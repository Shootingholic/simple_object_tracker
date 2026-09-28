#include <cstdint>
#include <gtest/gtest.h>

// Function verifying camera dimension parameters
bool validate_camera_params(int width, int height, double fps) {
  constexpr std::int64_t max_image_pixels = 1920LL * 1080LL;
  if (width <= 0 || width > 1920 || height <= 0 || height > 1080 ||
      static_cast<std::int64_t>(width) * height > max_image_pixels ||
      fps <= 0.0) {
    return false;
  }
  return true;
}

TEST(WebcamPublisherTest, ValidParameters) {
  EXPECT_TRUE(validate_camera_params(640, 480, 30.0));
  EXPECT_TRUE(validate_camera_params(1920, 1080, 30.0));
}

TEST(WebcamPublisherTest, InvalidParameters) {
  EXPECT_FALSE(validate_camera_params(-1, 480, 30.0));
  EXPECT_FALSE(validate_camera_params(640, 0, 30.0));
  EXPECT_FALSE(validate_camera_params(1921, 1080, 30.0));
  EXPECT_FALSE(validate_camera_params(1920, 1081, 30.0));
  EXPECT_FALSE(validate_camera_params(1920, 1080, -5.0));
}

int main(int argc, char **argv) {
  testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
