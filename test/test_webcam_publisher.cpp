#include <gtest/gtest.h>

// Function verifying camera dimension parameters
bool validate_camera_params(int width, int height, double fps) {
  if (width <= 0 || height <= 0 || fps <= 0.0) {
    return false;
  }
  return true;
}

TEST(WebcamPublisherTest, ValidParameters) {
  EXPECT_TRUE(validate_camera_params(640, 480, 30.0));
}

TEST(WebcamPublisherTest, InvalidParameters) {
  EXPECT_FALSE(validate_camera_params(-1, 480, 30.0));
  EXPECT_FALSE(validate_camera_params(640, 0, 30.0));
  EXPECT_FALSE(validate_camera_params(640, 480, -5.0));
}

int main(int argc, char **argv) {
  testing::InitGoogleTest(&argc, argv);
  return RUN_ALL_TESTS();
}
